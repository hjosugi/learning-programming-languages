//! freq: the application library behind the `wordfreq` CLI.
//!
//! Given a chunk of text, produce a ranked list of word frequencies. This is
//! where the data structures meet real input handling, so it exercises:
//!
//!   * explicit allocators -> `count` takes an allocator and returns an owned
//!                            slice; the caller frees it via `freeCounts`.
//!   * error unions/sets   -> `count` returns `CountError!...`; the public
//!                            `CountError` set names every failure mode.
//!   * optionals           -> `topWord` returns `?Entry` (empty input -> null).
//!   * slices              -> input is `[]const u8`; words are sub-slices.
//!   * comptime generic use-> ranking is collected into `DynArray(Entry)`.
//!
//! Ownership rule (important and idiomatic): the returned `[]Entry` and every
//! `Entry.word` inside it are heap-allocated copies owned by the caller. Use
//! `freeCounts` to release them. We copy the words because the keys must
//! outlive the input buffer (the CLI frees the input before printing).

const std = @import("std");
const Allocator = std.mem.Allocator;
const DynArray = @import("dyn_array.zig").DynArray;

/// One word and how many times it appeared.
pub const Entry = struct {
    word: []const u8,
    freq: u32,
};

/// Everything `count` can fail with. Built by unioning the std error set we
/// propagate (`Allocator.Error`) with this module's own cases. Naming the set
/// lets callers exhaustively `switch` on errors.
pub const CountError = Allocator.Error;

/// A word is a maximal run of ASCII letters/digits; everything else is a
/// separator. Comparison is case-insensitive ("The" == "the").
fn isWordByte(c: u8) bool {
    return std.ascii.isAlphanumeric(c);
}

/// Count word frequencies in `text` and return them ranked: highest frequency
/// first, ties broken alphabetically. The caller owns the result and must call
/// `freeCounts` with the same allocator.
pub fn count(gpa: Allocator, text: []const u8) CountError![]Entry {
    // StringHashMap keys are the lowercased word copies we own; values are counts.
    var map = std.StringHashMap(u32).init(gpa);
    // On any error after this point we must not leak the keys we inserted.
    defer {
        var it = map.iterator();
        while (it.next()) |kv| gpa.free(kv.key_ptr.*);
        map.deinit();
    }

    // Scratch buffer for lowercasing the current word before we look it up.
    var scratch: DynArray(u8) = .empty;
    defer scratch.deinit(gpa);

    var i: usize = 0;
    while (i < text.len) {
        // Skip separators.
        if (!isWordByte(text[i])) {
            i += 1;
            continue;
        }
        // Take the maximal word slice [start, i).
        const start = i;
        while (i < text.len and isWordByte(text[i])) : (i += 1) {}
        const raw = text[start..i]; // a sub-slice of the input, no copy yet

        scratch.clearRetainingCapacity();
        for (raw) |c| try scratch.append(gpa, std.ascii.toLower(c));
        const lowered = scratch.items(); // []u8 view into scratch (borrowed)

        // INVARIANT we rely on for clean teardown: the map only ever holds keys
        // it owns. So we look up first; only on a genuine miss do we dupe the
        // key and insert the *owned* copy. Doing the lookup with the borrowed
        // `lowered` and inserting the owned copy separately means a `dupe`
        // failure never leaves a borrowed (non-heap) key inside the map — which
        // would otherwise make the cleanup `defer` free a stack slice and crash.
        if (map.getPtr(lowered)) |value_ptr| {
            value_ptr.* += 1;
        } else {
            const owned = try gpa.dupe(u8, lowered);
            errdefer gpa.free(owned); // if `put` itself fails, don't leak the copy
            try map.put(owned, 1);
        }
    }

    // Collect entries into a DynArray so we can sort them. While we build this
    // vector, each `Entry.word` only *borrows* a map key — ownership stays with
    // the map. That keeps cleanup unambiguous: if anything below fails, the map
    // `defer` (and only it) frees the words, and this `errdefer` frees just the
    // entries buffer. Ownership transfers to the caller all at once at the end.
    var entries: DynArray(Entry) = .empty;
    errdefer entries.deinit(gpa);

    var it = map.iterator();
    while (it.next()) |kv| {
        try entries.append(gpa, .{ .word = kv.key_ptr.*, .freq = kv.value_ptr.* });
    }

    // `toOwnedSlice` may reallocate (and thus fail). If it fails here, `entries`
    // still owns its buffer (freed by the errdefer) and the map still owns every
    // word (freed by the defer) — no double free, no leak.
    const result = try entries.toOwnedSlice(gpa);

    // Success: the words now belong to `result`. Detach them from the map so the
    // map `defer` frees only its table, not the keys we just handed off.
    map.clearRetainingCapacity();

    // Sort: frequency descending, then word ascending for stable, readable output.
    std.mem.sort(Entry, result, {}, lessThan);
    return result;
}

/// Sort comparator: higher frequency first; alphabetical on ties.
fn lessThan(_: void, a: Entry, b: Entry) bool {
    if (a.freq != b.freq) return a.freq > b.freq;
    return std.mem.lessThan(u8, a.word, b.word);
}

/// Free a result returned by `count`, including every owned word.
pub fn freeCounts(gpa: Allocator, entries: []Entry) void {
    for (entries) |e| gpa.free(e.word);
    gpa.free(entries);
}

/// Convenience: the single most frequent word, or `null` for empty input.
/// Returns an optional so "no words at all" is impossible to mishandle.
pub fn topWord(gpa: Allocator, text: []const u8) CountError!?Entry {
    const entries = try count(gpa, text);
    defer freeCounts(gpa, entries);
    if (entries.len == 0) return null;
    // Copy the word out so it survives `freeCounts`.
    return Entry{ .word = try gpa.dupe(u8, entries[0].word), .freq = entries[0].freq };
}

// ----------------------------------------------------------------------------
// Tests. Every test uses std.testing.allocator: if `count`/`freeCounts` leak a
// single word copy or the entries slice, the test run fails.
// ----------------------------------------------------------------------------

const testing = std.testing;

test "empty input yields no entries (leak-safe)" {
    const entries = try count(testing.allocator, "");
    defer freeCounts(testing.allocator, entries);
    try testing.expectEqual(@as(usize, 0), entries.len);
}

test "single word counted once" {
    const entries = try count(testing.allocator, "hello");
    defer freeCounts(testing.allocator, entries);

    try testing.expectEqual(@as(usize, 1), entries.len);
    try testing.expectEqualStrings("hello", entries[0].word);
    try testing.expectEqual(@as(u32, 1), entries[0].freq);
}

test "case-insensitive and punctuation-splitting" {
    const entries = try count(testing.allocator, "The the THE, dog! Dog?");
    defer freeCounts(testing.allocator, entries);

    try testing.expectEqual(@as(usize, 2), entries.len);
    // "the" has 3, "dog" has 2 -> "the" ranks first.
    try testing.expectEqualStrings("the", entries[0].word);
    try testing.expectEqual(@as(u32, 3), entries[0].freq);
    try testing.expectEqualStrings("dog", entries[1].word);
    try testing.expectEqual(@as(u32, 2), entries[1].freq);
}

test "ranking: frequency desc, then alphabetical on ties" {
    // "banana" x2, "apple" x1, "cherry" x1 -> banana, apple, cherry.
    const entries = try count(testing.allocator, "banana cherry apple banana");
    defer freeCounts(testing.allocator, entries);

    try testing.expectEqual(@as(usize, 3), entries.len);
    try testing.expectEqualStrings("banana", entries[0].word);
    try testing.expectEqualStrings("apple", entries[1].word);
    try testing.expectEqualStrings("cherry", entries[2].word);
}

test "digits are word characters" {
    const entries = try count(testing.allocator, "room 101 room 101 room");
    defer freeCounts(testing.allocator, entries);

    try testing.expectEqual(@as(usize, 2), entries.len);
    try testing.expectEqualStrings("room", entries[0].word);
    try testing.expectEqual(@as(u32, 3), entries[0].freq);
    try testing.expectEqualStrings("101", entries[1].word);
    try testing.expectEqual(@as(u32, 2), entries[1].freq);
}

test "topWord returns an optional" {
    const top = try topWord(testing.allocator, "go go go stop");
    try testing.expect(top != null);
    defer testing.allocator.free(top.?.word);
    try testing.expectEqualStrings("go", top.?.word);
    try testing.expectEqual(@as(u32, 3), top.?.freq);

    const none = try topWord(testing.allocator, "   ...  ");
    try testing.expectEqual(@as(?Entry, null), none);
}

test "OutOfMemory propagates and leaks nothing (failing allocator, error path)" {
    // std.testing.checkAllAllocationFailures runs `count` repeatedly, failing a
    // different allocation each time, and asserts every partial run frees
    // everything it allocated. This is the rigorous proof of leak-safety on the
    // error path — exactly what explicit allocators make possible.
    const Ctx = struct {
        fn run(gpa: Allocator) !void {
            const entries = try count(gpa, "alpha beta beta gamma gamma gamma");
            defer freeCounts(gpa, entries);
            try testing.expectEqual(@as(usize, 3), entries.len);
        }
    };
    try testing.checkAllAllocationFailures(testing.allocator, Ctx.run, .{});
}
