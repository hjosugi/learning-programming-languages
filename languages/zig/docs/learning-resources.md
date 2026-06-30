# Further learning resources

Last verified: 2026-06-30

Curated hands-on Zig resources (2026 edition) plus the canonical primary sources
for this repo's named learning targets: comptime generics, explicit allocators
and memory ownership, error sets / error unions, optionals, slices and strings,
and the build system. Zig is pre-1.0 and moves fast, so pin every resource to
the version it targets — this repo's code targets **Zig 0.16** (see the
`std.process.Init` entry point in `src/main.zig`).

## Start in the browser (no install)

- **LearningZig.org** — https://learningzig.org
  A 25-lesson structured curriculum with a runnable Playground in every chapter,
  tracking Zig 0.16. Beginner track (variables/types → functions → control flow
  → arrays/structs → enums and tagged unions) then intermediate (error handling,
  `Allocator`, `comptime`, optionals, slices, pointers, strings, generics) maps
  almost one-to-one onto the modules in this repo.

- **Zig Playground (official)** — https://playground.ziglang.org
  Run and share Zig snippets in the browser with no install. The fastest way to
  try a single feature (a `comptime` block, an error union, an optional) before
  wiring it into `src/`.

## Official and semi-official

- **Official documentation** — https://ziglang.org/documentation/master/
  The language reference and standard-library docs. A Japanese translation is
  available under https://ziglang.org/ja-JP/ . The authoritative answer for
  exact semantics of `comptime`, error sets, optionals, slices, and `defer` /
  `errdefer`.

- **zig.guide** — https://zig.guide
  The community tutorial (tracking Zig 0.15.2): Installation → language → standard
  library → build system → C interop. The build-system and std chapters are the
  direct background for `build.zig` and this repo's use of `std.StringHashMap`,
  `std.mem.sort`, and `std.testing`.

- **ziglings/exercises** — https://codeberg.org/ziglings/exercises
  "Fix the small broken program" drills — the Zig answer to Rustlings. The best
  way to practice the same error-handling and optional patterns this repo's tests
  assert, one tiny failing program at a time.

## Books and structured guides

- **Zen of Zig — Volume 1: Fundamentals** — https://zenofzig.com
  A current book targeting Zig 0.16.0 with 90+ runnable samples (available on
  Leanpub). Matches the version this repo's code is written against.

- **Karl Seguin — Learning Zig** — https://www.openmymind.net/learning_zig/
  A well-regarded practical guide. Its chapters on the allocator model, slices,
  and error handling are the conceptual companion to `freq.zig`'s
  caller-owns-the-result discipline.

- **zig-cookbook** — https://github.com/zigcc/zig-cookbook
  Task-oriented recipes for common jobs (files, strings, JSON, processes) — reach
  for it when you want the idiomatic shape of a concrete task rather than a
  full tutorial.

## Video and courses

- **Pragmatic AI Labs — "Zig From Zero" (Coursera, ~4h)** —
  https://www.coursera.org/learn/zig-from-zero
  A short course framed around when to choose Zig vs Rust for Lambda / edge /
  embedded targets.

- **Exercism — Zig track** — https://exercism.org/tracks/zig
  98 graded exercises with free mentoring; complements ziglings with
  problem-solving practice and feedback.

- **ChariotSolutions — "The Road to Zig 1.0" (YouTube, ~1h)** —
  https://www.youtube.com/watch?v=Gv2I7qTux7g
  Andrew Kelley (Zig's author) on the language's design and direction.

- **Zig SHOWTIME ep.41 — 2026 roadmap** — https://www.youtube.com/c/ZigSHOWTIME
  Community show; the 2026-roadmap episode covers the async story. Useful context
  for `std.Io`, which `src/main.zig` already threads explicitly.

## Japanese-language resources (日本語)

- **Qiita「やさしく学ぶ Zig 入門ガイド」** — https://qiita.com
  Beginner guide (posted 2026-01, updated 2026-02): Windows/Unix install through
  `comptime`, covered systematically.

- **Qiita「Zig 0.16・Mojo 1.0 Beta 登場で変わった次世代言語の勢力図」** —
  https://qiita.com (2026-06-17)
  A current 0.16 overview with detail on `std.Io` — relevant to the `std.Io`
  reader/writer plumbing in `src/main.zig`.

- **youngju.dev「モダン Zig 2026」** — https://youngju.dev
  (2026-05, Japanese edition available) Walks through Bun / TigerBeetle / Ghostty
  / `comptime` / Zon as real-world Zig.

- **Built with Zig** — https://builtwithzig.com
  A categorized catalog of projects written in Zig — useful for seeing where the
  fundamentals in this repo lead.

## How these map to this repo

- **comptime generics** → `DynArray(comptime T: type)` and
  `RingBuffer(comptime T: type)` in `src/dyn_array.zig` / `src/ring_buffer.zig`.
- **explicit allocators / ownership** → `freq.count` returns a caller-owned
  slice freed by `freq.freeCounts`; `src/dyn_array.zig` stores no allocator.
- **error sets and unions** → `CliError` (`src/main.zig`), `CountError`
  (`src/freq.zig`), `IndexError` (`src/dyn_array.zig`), `PushError`
  (`src/ring_buffer.zig`).
- **optionals** → `pop`, `getOrNull`, `last`, `peek`, and `freq.topWord`.
- **slices and strings** → `[]const u8` input and sub-slice words in `freq.zig`;
  `items()` views in `dyn_array.zig`.
- **build system / testing** → `build.zig` and the `test {}` aggregator in
  `src/main.zig` that pulls every module into one `zig test` binary.
