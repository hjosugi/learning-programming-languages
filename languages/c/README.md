# Learning C

Hands-on C focused on the things C actually makes you confront: **pointers and
manual memory management**, **structs**, **header/implementation separation**, a
**Makefile** build, **assert-based unit tests**, and **AddressSanitizer**.

The flagship hands-on is a real **separate-chaining hash table** built and
tested under strict warnings and sanitizers — not a toy.

Last verified: 2026-06-21

## Runnable Hands-On

A separate-chaining hash table (string keys, `long` values) with header/impl
split, manual `malloc`/`free` with documented ownership, growth + rehash, an
assert-based test suite, and an ASan/UBSan target. See
[hashtable/README.md](hashtable/README.md).

Run the demo:

```bash
make -C languages/c/hashtable run
```

Run the test suite (non-interactive, exits non-zero on failure):

```bash
make -C languages/c/hashtable test
```

Run the tests under AddressSanitizer + UndefinedBehaviorSanitizer (proves no
leaks, no UB):

```bash
make -C languages/c/hashtable asan
```

Everything uses `-Wall -Wextra -Werror -std=c17`, builds offline, and works with
both `gcc` and `clang` (`make ... CC=clang`).

## How this repo is organized

```text
learning-c/
  README.md                     this file
  .gitignore                    ignores C build artifacts (bin/, *.o, ...)
  docs/
    2026-learning-items.md      named learning targets + Definition of Done
    learning-resources.md       canonical primary sources (cppreference, K&R, ...)
  hashtable/                    the hands-on project
    README.md                   Run / Test / Walkthrough / Upgrade path / Exercises
    Makefile                    all / run / test / asan / clean
    src/hashtable.h             public API + ownership contract
    src/hashtable.c             implementation
    src/main.c                  narrated demo
    tests/test_hashtable.c      assert-based test suite (11 cases)
```

## What this repo teaches

- **Pointers and memory ownership.** Who allocates, who frees, who merely
  borrows — written into the header and enforced by ASan.
- **Structs** as the building block of every C data structure.
- **Header/implementation separation** with header guards and `static`
  internals (C's "private").
- **A Makefile build** with the targets you actually want: build, run, test,
  sanitize, clean.
- **Testing without a framework**, using `assert()` and a tiny runner.
- **Sanitizers** (`-fsanitize=address,undefined`) as the everyday safety net for
  C.

## What does not belong here

- Embedded/MCU C — see `learning-embedded-iot`.
- Build-tool theory (Bazel/Nix/CMake-as-a-topic) — see `learning-build-systems`.
- C++ / RAII / templates — that is a different language and a different repo.

## Further learning

- Named targets and Definition of Done: [docs/2026-learning-items.md](docs/2026-learning-items.md)
- Canonical references (cppreference, the C standard drafts, K&R, the sanitizer
  docs): [docs/learning-resources.md](docs/learning-resources.md)
