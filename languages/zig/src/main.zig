//! wordfreq: a small CLI that ranks word frequencies in text.
//!
//! Usage:
//!   wordfreq            read text from stdin (falls back to the bundled sample
//!                       when stdin is an interactive terminal)
//!   wordfreq <file>     read text from the given file
//!   wordfreq --top N    show only the top N words (default: all)
//!
//! This file is also the single entry point for the test suite. The `test {}`
//! block near the bottom imports every module so that
//! `zig test src/main.zig` runs ALL tests in the project in one binary.

const std = @import("std");
const Allocator = std.mem.Allocator;
const File = std.Io.File;

const freq = @import("freq.zig");
const DynArray = @import("dyn_array.zig").DynArray;
const RingBuffer = @import("ring_buffer.zig").RingBuffer;

/// Path used when no input is supplied and stdin is interactive.
const sample_path = "data/sample.txt";

/// Zig 0.16 entry point. Taking `std.process.Init` (instead of a bare `main`)
/// hands us, already wired up:
///   * `init.gpa`           a leak-checking general-purpose allocator,
///   * `init.io`            the standard blocking `Io` implementation,
///   * `init.arena`         a process-lifetime arena (auto-freed at exit),
///   * `init.minimal.args`  the command-line arguments.
/// The runtime cleans all of this up after `main` returns, including the
/// leak report, so we thread these explicitly rather than building our own.
pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const io = init.io;
    const arena = init.arena.allocator();

    // Buffered stdout. `flush` at the end actually writes it out.
    var out_buf: [4096]u8 = undefined;
    var stdout_writer = File.stdout().writer(io, &out_buf);
    const out = &stdout_writer.interface;

    run(gpa, arena, io, out, init.minimal.args) catch |err| {
        // Report errors to stderr and exit non-zero so scripts can detect failure.
        var err_buf: [256]u8 = undefined;
        var stderr_writer = File.stderr().writer(io, &err_buf);
        const errw = &stderr_writer.interface;
        errw.print("wordfreq: error: {s}\n", .{@errorName(err)}) catch {};
        errw.flush() catch {};
        std.process.exit(1);
    };

    try out.flush();
}

/// Parsed command-line options.
const Options = struct {
    file_path: ?[]const u8 = null, // optional explicit input file
    top: ?usize = null, // optional limit on rows printed
};

/// This module's own named error set. `parseArgs` returns it as part of an
/// inferred error union (`!Options`), alongside the std errors it lets
/// propagate. Naming the set lets callers exhaustively reason about failure.
const CliError = error{InvalidTopArgument};

/// The real work, separated from `main` so error handling lives in one place.
/// `tmp` is a short-lived allocator (the arena) used for argv; `gpa` is the
/// leak-checked allocator used for everything whose lifetime we manage by hand.
fn run(gpa: Allocator, tmp: Allocator, io: std.Io, out: *std.Io.Writer, args: std.process.Args) !void {
    const opts = try parseArgs(tmp, args);

    // Acquire the input text. `defer` frees it regardless of which branch ran.
    const text = try readInput(gpa, io, opts.file_path);
    defer gpa.free(text);

    const entries = try freq.count(gpa, text);
    defer freq.freeCounts(gpa, entries);

    // Decide how many rows to print using an optional with a default.
    const limit = if (opts.top) |n| @min(n, entries.len) else entries.len;

    try out.print("# word frequencies ({d} unique words)\n", .{entries.len});
    for (entries[0..limit]) |e| {
        try out.print("{d:>6}  {s}\n", .{ e.freq, e.word });
    }

    // Demonstrate the RingBuffer on real data: keep a sliding window of the last
    // few printed words and echo it as a "recent ranking" footer.
    if (limit > 0) {
        const window: usize = 3;
        var recent = try RingBuffer([]const u8).init(gpa, window);
        defer recent.deinit(gpa);
        for (entries[0..limit]) |e| _ = recent.pushOverwrite(e.word);

        try out.print("\n# last {d} of the printed ranking (via RingBuffer): ", .{recent.count()});
        var first = true;
        while (recent.pop()) |word| {
            if (!first) try out.writeAll(", ");
            try out.writeAll(word);
            first = false;
        }
        try out.writeByte('\n');
    }
}

/// Parse the value following `--top` into a row limit, mapping any non-numeric
/// (or otherwise invalid) text to this module's named `error.InvalidTopArgument`.
/// Factored out of `parseArgs` so the error path is directly unit-testable.
fn parseTopValue(value: []const u8) CliError!usize {
    return std.fmt.parseInt(usize, value, 10) catch CliError.InvalidTopArgument;
}

/// Parse argv into `Options`. Returns a named error on a bad `--top` value.
/// `tmp` is an arena, so the materialized argv slice needs no manual free.
fn parseArgs(tmp: Allocator, args: std.process.Args) !Options {
    const argv = try args.toSlice(tmp);

    var opts: Options = .{};
    var i: usize = 1; // skip argv[0] (program name)
    while (i < argv.len) : (i += 1) {
        const arg = argv[i];
        if (std.mem.eql(u8, arg, "--top")) {
            i += 1;
            if (i >= argv.len) return CliError.InvalidTopArgument;
            opts.top = try parseTopValue(argv[i]);
        } else {
            // First non-flag argument is the input file path.
            opts.file_path = arg;
        }
    }
    return opts;
}

/// Read the full input as an owned byte slice. Source priority:
///   1. explicit file path,
///   2. stdin if it is piped (not a terminal),
///   3. the bundled sample file (used both when stdin is an interactive
///      terminal and when stdin is connected but empty, so a plain
///      `zig run src/main.zig` always prints something interesting).
fn readInput(gpa: Allocator, io: std.Io, file_path: ?[]const u8) ![]u8 {
    if (file_path) |path| return readFile(gpa, io, path);

    // If stdin is a pipe/redirect, consume it; otherwise fall back to the sample.
    const stdin = File.stdin();
    if (!try stdin.isTty(io)) {
        var in_buf: [4096]u8 = undefined;
        var reader = stdin.reader(io, &in_buf);
        const piped = try reader.interface.allocRemaining(gpa, .unlimited);
        if (piped.len > 0) return piped;
        // Empty stdin (e.g. `zig run` with no input redirected): use the sample.
        gpa.free(piped);
    }

    return readFile(gpa, io, sample_path);
}

/// Read an entire file into an owned byte slice.
fn readFile(gpa: Allocator, io: std.Io, path: []const u8) ![]u8 {
    const file = try std.Io.Dir.cwd().openFile(io, path, .{});
    defer file.close(io);

    var buf: [4096]u8 = undefined;
    var reader = file.reader(io, &buf);
    return reader.interface.allocRemaining(gpa, .unlimited);
}

// ----------------------------------------------------------------------------
// Test aggregator: importing a module pulls its tests into THIS test binary, so
// `zig test src/main.zig` runs every test in the project in one shot.
// ----------------------------------------------------------------------------

test {
    _ = @import("dyn_array.zig");
    _ = @import("ring_buffer.zig");
    _ = @import("freq.zig");
}

const testing = std.testing;

test "limit math: absent --top means print everything" {
    const entries_len: usize = 7;
    const opt_top: ?usize = null;
    const limit = if (opt_top) |n| @min(n, entries_len) else entries_len;
    try testing.expectEqual(@as(usize, 7), limit);
}

test "limit math: --top clamps to available rows" {
    const entries_len: usize = 2;
    const opt_top: ?usize = 5;
    const limit = if (opt_top) |n| @min(n, entries_len) else entries_len;
    try testing.expectEqual(@as(usize, 2), limit);
}

test "--top with a non-numeric value yields error.InvalidTopArgument (error path)" {
    try testing.expectError(error.InvalidTopArgument, parseTopValue("notanumber"));
    try testing.expectError(error.InvalidTopArgument, parseTopValue("-1"));
    // A valid value parses to the expected usize.
    try testing.expectEqual(@as(usize, 5), try parseTopValue("5"));
}
