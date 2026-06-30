# 2026 Learning Items: Zig

Last verified: 2026-06-30

The named learning targets for this repo, each mapped to where the `wordfreq`
CLI and its two data structures (`DynArray`, `RingBuffer`) exercise it. The
hands-on resources that teach each target are in
[learning-resources.md](learning-resources.md).

## Must Learn

### comptime generics

- `fn DynArray(comptime T: type) type` — a function that runs at compile time
  and returns a *type*; types are values you can compute
- each distinct `T` produces a distinct, fully monomorphized type (no runtime
  type tags)
- the `const Self = @This()` pattern for a generated struct type
- `.empty` as the canonical zero value instead of a separate `init`

Exercised in: `src/dyn_array.zig` (`DynArray(T)`), `src/ring_buffer.zig`
(`RingBuffer(T)`); used over `u8`, `i32`, `Entry`, `[]const u8`, and an inline
`Point` struct in the tests.

Outcome:

- Instantiate `DynArray`/`RingBuffer` over a new element type and explain why no
  cast is needed.
- Explain what "monomorphized at comptime" buys over a runtime-tagged container.

### Explicit allocators and memory ownership

- every operation that may allocate takes an `std.mem.Allocator`; the container
  stores no allocator, so it can be moved between allocators
- the caller-owns-the-result contract: `freq.count` returns an owned slice the
  caller frees with `freq.freeCounts`
- `defer` / `errdefer` for release-on-all-paths and release-only-on-failure
- `gpa.dupe` to copy keys that must outlive the input buffer
- ownership *hand-off*: `toOwnedSlice` and detaching keys from the map on success
- leak-checking with `std.testing.allocator` and
  `std.testing.checkAllAllocationFailures`

Exercised in: `src/freq.zig` (`count`/`freeCounts`/`topWord`, the failing-
allocator test), `src/dyn_array.zig` (`ensureCapacity`, `toOwnedSlice`),
`src/ring_buffer.zig` (`init`/`deinit`).

Outcome:

- State who allocates and who frees for any value crossing a function boundary.
- Explain why the failing-allocator test proves leak-safety on the error path.

### Error sets and error unions

- defining a small, named error set (`error{...}`) per failure domain
- inferred error unions (`!T`) vs an explicit set (`CliError!usize`)
- `try`, `catch`, and mapping a foreign error to your own
  (`parseInt(...) catch CliError.InvalidTopArgument`)
- asserting the exact error with `testing.expectError`

Exercised in: `src/main.zig` (`CliError.InvalidTopArgument` from
`parseTopValue`/`parseArgs`), `src/freq.zig` (`CountError`), `src/dyn_array.zig`
(`IndexError.IndexOutOfBounds`), `src/ring_buffer.zig`
(`PushError.BufferFull`).

Outcome:

- Add a new error variant and a test that asserts exactly it.
- Explain when "missing/full" should be an error vs an optional.

### Optionals

- `?T` for "maybe absent", forcing the caller to handle the empty case
- payload-capturing `if (opt) |x|` and `while (q.pop()) |x|`
- choosing optional vs error for the same condition (`getOrNull` vs `get`)

Exercised in: `src/dyn_array.zig` (`pop`, `last`, `getOrNull`),
`src/ring_buffer.zig` (`pop`, `peek`), `src/freq.zig` (`topWord` returns
`?Entry`), `src/main.zig` (`opts.top: ?usize`, the `--top` limit math).

Outcome:

- Replace a sentinel return with `?T` and update the call site.
- Justify why `getOrNull` returns `null` but `get` returns an error.

### Slices and strings

- `[]T` / `[]const u8` as pointer-plus-length views, not owners
- sub-slicing the input (`text[start..i]`) without copying
- a borrowed view (`items()`) invalidated by any reallocation
- `@memcpy` into a destination sized to match
- ASCII string handling: `std.ascii.toLower`, case-insensitive lookup

Exercised in: `src/freq.zig` (word sub-slices, lowercase scratch buffer),
`src/dyn_array.zig` (`items`, `appendSlice`, `@memcpy`), `src/ring_buffer.zig`
(`copyToSlice`).

Outcome:

- Explain why `items()` must not be held across an `append`.
- Distinguish a borrowed sub-slice from an owned `dupe`d copy.

### The build system and `zig test`

- file-first commands (`zig run`/`zig test src/main.zig`) vs the build graph
- `build.zig`: modules, `addExecutable`, `addTest`, named steps
- `-Doptimize` release modes and `-Dtarget` cross-compilation
- the `test {}` aggregator that imports every module so one `zig test` binary
  runs the whole suite

Exercised in: `build.zig` (`run`/`test` steps), `src/main.zig` (the `test {}`
block importing `dyn_array`, `ring_buffer`, `freq`).

Outcome:

- Run the suite both ways (`zig test src/main.zig` and `zig build test`).
- Add a module and wire it into the aggregator so its tests run.

## Definition of Done

- `zig build run` (or `zig run src/main.zig`) prints a ranked word-frequency
  table and exits non-zero on a bad `--top` value.
- `zig build test` (or `zig test src/main.zig`) passes, including the
  failing-allocator leak-safety test and every error-path `expectError`.
- Tests use `std.testing.allocator`, so any leak fails the run; the build uses
  std only and works fully offline.
- Each named learning target above has at least one concrete location in `src/`
  and a passing test that exercises it.
- README documents Run and the further-learning links.

## Tradeoff Questions

Ask these as the project grows:

- Should this "absent/full" case be an **optional** (`?T`, ordinary outcome) or
  an **error** (`error{...}`, exceptional)?
- Should the API take the allocator per-call (movable, like `DynArray`) or store
  it once at `init` (simpler call sites, like a stored-allocator container)?
- Is this a **borrow** (a slice into existing memory) or an **owned copy**
  (`dupe`)? Who frees it, and is that documented?
- Should this run at **comptime** (specialized type, zero runtime cost) or carry
  a runtime tag (a tagged union) instead?
- Does graduating to `build.zig` earn its keep here, or do the file-first
  `zig run`/`zig test` commands still suffice for the learning goal?

## Going further (covered by the resources, not yet by the code)

- **enums and tagged unions** — model `Value`-style sum types (see LearningZig's
  enum/tagged-union lessons); a natural next data structure for this repo.
- **`std.Io` and async** — `src/main.zig` already threads `std.Io` explicitly;
  the 2026-roadmap talks in [learning-resources.md](learning-resources.md) cover
  where async is headed.
- **C interop** — zig.guide's C chapter, for calling into / building C from Zig.
