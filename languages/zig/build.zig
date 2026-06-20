//! build.zig — the upgrade path from `zig run`/`zig test` to a real build graph.
//!
//! The primary day-to-day commands in this repo are the simple, version-robust
//!     zig run  src/main.zig
//!     zig test src/main.zig
//! This file exists so you can *graduate* to the Zig build system, which is how
//! real Zig projects manage modules, release modes, cross-compilation, and
//! multi-step pipelines. With Zig 0.16 on PATH you would run:
//!
//!     zig build            # compile the wordfreq executable
//!     zig build run        # build and run it (pass args after `--`)
//!     zig build test       # build and run the whole unit-test suite
//!     zig build -Doptimize=ReleaseFast   # an optimized release build
//!     zig build -Dtarget=aarch64-linux   # cross-compile
//!
//! Note: in THIS environment `zig` is reached via `mise exec -- zig`, e.g.
//!     mise exec -- zig build test
//! The simple file-based commands in the README are what the verifier runs.

const std = @import("std");

pub fn build(b: *std.Build) void {
    // Standard options let the CLI user pick the target and optimize mode:
    //   -Dtarget=...    cross-compilation triple (default: host)
    //   -Doptimize=...  Debug | ReleaseSafe | ReleaseFast | ReleaseSmall
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // A Module is the unit the compiler imports. Our root module is main.zig;
    // it `@import`s the sibling files directly, so they are pulled in as part of
    // the same module graph without extra wiring.
    const root_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // The wordfreq executable.
    const exe = b.addExecutable(.{
        .name = "wordfreq",
        .root_module = root_module,
    });
    b.installArtifact(exe);

    // `zig build run` — build then execute, forwarding args after `--`.
    const run_step = b.step("run", "Build and run the wordfreq CLI");
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    if (b.args) |args| run_cmd.addArgs(args);
    run_step.dependOn(&run_cmd.step);

    // `zig build test` — compile and run the unit tests in one step. Because
    // main.zig imports every module (and has a `test {}` aggregator), this single
    // test artifact covers DynArray, RingBuffer, and freq.
    const test_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    const unit_tests = b.addTest(.{
        .name = "wordfreq-tests",
        .root_module = test_module,
    });
    const run_tests = b.addRunArtifact(unit_tests);

    const test_step = b.step("test", "Run the full unit-test suite");
    test_step.dependOn(&run_tests.step);
}
