# Further learning resources

Last verified: 2026-06-21

Curated, canonical primary sources for this repo's named learning targets: C
pointers and memory management, structs, header/impl separation, Make,
assert-based testing, and the sanitizers. Prefer these over blog posts.

## C language and standard library

- **cppreference — C reference** — https://en.cppreference.com/w/c
  The best continuously maintained reference for the C standard library and
  language. Use it for exact semantics of `malloc`/`calloc`/`realloc`/`free`,
  `string.h`, `assert.h`, and `<stdint.h>` fixed-width types.

- **The C Programming Language, 2nd ed. (Kernighan & Ritchie, "K&R")** —
  https://www.cs.princeton.edu/~bwk/cbook.html
  The canonical book. Chapter 5 (pointers and arrays) and Chapter 6 (structures)
  are the direct background for this hash table; the symbol-table example in K&R
  is essentially this project.

- **ISO/IEC 9899 (the C standard) — public committee drafts** —
  https://www.open-std.org/jtc1/sc22/wg14/
  The WG14 home page links the working drafts (e.g. N2310 for C17/C18). The
  authoritative answer to "is this defined behaviour?" — including that
  `free(NULL)` is a no-op and the rules behind `-fsanitize=undefined`.

- **GNU C Library (glibc) manual — Memory Allocation** —
  https://www.gnu.org/software/libc/manual/html_node/Memory-Allocation.html
  How the allocator this repo links against actually behaves; good companion to
  the standard's abstract description.

## Build tooling: Make

- **GNU Make manual** — https://www.gnu.org/software/make/manual/
  The reference for targets, prerequisites, variables, `.PHONY`, and order-only
  prerequisites (`|`) — all used in this project's `Makefile`.

## Testing and sanitizers

- **assert — cppreference** — https://en.cppreference.com/w/c/error/assert
  Exact semantics of `assert()` and how `NDEBUG` disables it (why the test
  build must not define `NDEBUG`).

- **AddressSanitizer (Clang docs)** — https://clang.llvm.org/docs/AddressSanitizer.html
  What ASan detects (use-after-free, heap-buffer-overflow, leaks via LSan) and
  the `ASAN_OPTIONS` knobs. gcc implements the same `-fsanitize=address`.

- **UndefinedBehaviorSanitizer (Clang docs)** —
  https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
  The checks behind `-fsanitize=undefined` and `UBSAN_OPTIONS=halt_on_error=1`
  used by the `asan` Make target.

- **Valgrind documentation (Memcheck)** — https://valgrind.org/docs/manual/mc-manual.html
  The classic, independent leak/UB detector named in this project's upgrade
  path; complements the compiler sanitizers.

## Going further

- **CMake documentation** — https://cmake.org/cmake/help/latest/
  The reference for the "move from Make to CMake" upgrade step (library targets,
  `enable_testing`, `ctest`).

- **libFuzzer (Clang docs)** — https://llvm.org/docs/LibFuzzer.html
  Coverage-guided fuzzing for the upgrade-path fuzz harness
  (`-fsanitize=fuzzer,address`).
