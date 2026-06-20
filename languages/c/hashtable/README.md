# Hash Table (separate chaining) — C hands-on

A small but *real* hash table in C with proper **header/implementation
separation**, manual **malloc/free** with one clear owner per allocation,
**structs and pointers** throughout, an **assert-based test suite**, a
**Makefile** build, and an **AddressSanitizer + UBSan** target that proves the
code has no leaks or undefined behaviour.

Keys are C strings (the table owns a private copy of each); values are `long`.
Collisions are resolved by **separate chaining** (each bucket is a singly-linked
list), and the table **grows and rehashes** automatically to keep the load
factor under 0.75.

Last verified: 2026-06-21

## Layout

| File | Role |
| --- | --- |
| `src/hashtable.h` | public API + the **ownership contract** (read this first) |
| `src/hashtable.c` | implementation: hashing, chaining, grow/rehash, free |
| `src/main.c` | narrated demo (`make run`) |
| `tests/test_hashtable.c` | 11 `assert()`-based test cases (`make test`) |
| `Makefile` | `all` / `run` / `test` / `asan` / `clean` |

## Run

Needs only `gcc` (or `clang`) and `make`, both on PATH on this machine. No
network, no external libraries.

```bash
make -C languages/c/hashtable run
```

Or build the binary and run it yourself:

```bash
make -C languages/c/hashtable && languages/c/hashtable/bin/demo
```

Build with clang instead of gcc:

```bash
make -C languages/c/hashtable CC=clang run
```

## Test

Non-interactive; exits non-zero if any `assert()` fails (a failed assert aborts
with status 134, which fails the `make` rule):

```bash
make -C languages/c/hashtable test
```

Run the same suite under **AddressSanitizer + UndefinedBehaviorSanitizer** with
leak detection on (this is the proof of "no leaks"):

```bash
make -C languages/c/hashtable asan
```

All builds use `-Wall -Wextra -Werror -std=c17`, so any warning is a hard error.

## Walkthrough — the C concepts this code demonstrates

- **Header / implementation separation.** `hashtable.h` declares the API and
  documents the ownership rules; `hashtable.c` holds the logic. Callers include
  only the header and link against the compiled `.c`. The header guard
  (`#ifndef LEARNING_C_HASHTABLE_H`) prevents double inclusion. Internal helpers
  in the `.c` are marked `static` so they don't leak into the global symbol
  table — the C equivalent of "private".

- **Manual memory management with explicit ownership.** Every allocation has
  exactly one owner, written down in the header:
  - `ht_create` allocates the `hashtable` struct **and** the bucket array
    (`calloc`, so the chain heads start NULL). On bucket-allocation failure it
    frees the struct first so nothing leaks.
  - `ht_set` `malloc`s a **private copy of the key** (we ship our own
    `dup_str`, since POSIX `strdup` isn't in C17) and a node. If the node
    allocation fails *after* the key copy succeeds, it frees the copy — the
    classic "partial-failure cleanup" that leaks if you forget it.
  - `ht_free` walks every chain freeing `node->key` then `node`, then the
    bucket array, then the struct — in dependency order.
  - `ht_keys` hands back a **caller-owned array of borrowed string pointers**:
    you `free()` the array, the table keeps owning the strings. Mixing those up
    is the most common ownership bug in C; the contract spells it out.

- **Pointers, including pointer-to-pointer.** `ht_remove` walks the chain with
  `ht_entry **link` — a pointer to the link that points at the current node.
  That lets it splice a node out (`*link = node->next;`) without a separate
  `prev` variable and uniformly handles "remove the head" vs "remove the
  middle". This double-pointer list traversal is one of C's signature idioms.

- **Structs by value and by reference.** `ht_entry` and `hashtable` are plain
  structs; nodes are heap structs linked by `next`; the `long` value is stored
  **by value** inside the node while the key is stored **by reference** (a
  pointer to a heap copy). Knowing which is which is the ownership story.

- **A real growth policy.** Capacity is always a power of two, so
  `hash & (capacity - 1)` replaces a modulo. When `(size+1)/capacity` would
  exceed 3/4, `ht_resize` allocates a new bucket array and **re-buckets every
  existing node** (reusing the node objects — no key is copied or freed), then
  frees the old array. The allocations that can fail happen *before* the table
  is mutated, so an out-of-memory grow leaves the table fully intact.

- **Defensive programming.** Every public function tolerates a NULL table and a
  NULL key without crashing (no-op or sentinel return), mirroring how
  `free(NULL)` is defined to be safe. `test_null_defensive` exercises all of
  them.

- **assert-based testing.** No framework: each case is a function full of
  `assert()`s, registered in a small `{name, fn}` table and run in sequence. A
  failed `assert()` calls `abort()` → non-zero exit → `make test` fails. The
  Makefile deliberately does **not** define `NDEBUG`, so the asserts stay live.

## Upgrade path

This is a learning model. Here is how to grow it toward production C tooling:

1. **Split into a reusable library.** Compile `hashtable.c` to `libhashtable.a`
   (`ar rcs`) or a shared `.so`, install the header, and link the demo/tests
   against the archive. This separates "the library" from "its consumers".

2. **Move from Make to CMake.** Add a `CMakeLists.txt` with a `hashtable`
   library target, an `add_executable(demo …)`, and `enable_testing()` +
   `add_test`. Run with `ctest`. CMake scales to multi-target, multi-platform
   builds far better than a hand-written Makefile.

3. **Generalize the value type.** Store `void *` values (with an optional
   destructor callback) instead of `long`, so the table can hold anything. This
   forces you to extend the ownership contract to values, not just keys.

4. **Add fuzzing.** Wire up a libFuzzer or AFL++ harness that drives random
   sequences of `ht_set` / `ht_get` / `ht_remove` against a reference
   `std::map`-style oracle, built with `-fsanitize=fuzzer,address`. This finds
   edge cases hand-written tests miss.

5. **Add Valgrind alongside ASan.** `valgrind --leak-check=full --error-exitcode=1
   ./bin/test_hashtable` is a second, independent leak/UB check (Memcheck
   catches some things ASan doesn't and vice-versa).

6. **Run the sanitizers in CI.** A GitHub Actions matrix over `{gcc, clang}` ×
   `{test, asan}` (plus the Valgrind job) makes "no leaks, no UB, no warnings"
   a merge gate instead of a manual ritual.

## Exercises

Progressive — each builds on the table you have:

1. **Add `ht_iterate`.** Implement
   `void ht_iterate(const hashtable *, void (*fn)(const char *key, long value, void *ud), void *ud);`
   that visits every entry. Reimplement the demo's key listing on top of it, and
   add a test that sums all values via the callback.

2. **Shrink on removal.** Currently the table only grows. Add a *shrink* path:
   when `size/capacity` drops below 1/8 (and capacity > min), halve and rehash.
   Add a test that inserts 1000 keys, removes 990, and asserts the capacity
   went back down — while every remaining key still resolves.

3. **Track and assert chain length.** Add an internal function returning the
   longest bucket chain. Insert 10k random keys and assert the max chain stays
   small (say < 20) — empirical evidence that FNV-1a + power-of-two masking
   distributes well. Then swap in a deliberately bad hash (`return 0;`) and
   watch the assertion fail.

4. **Make values generic (`void *`).** Change `value` to `void *` plus an
   optional `void (*free_value)(void *)` set at `ht_create` time, called by
   `ht_remove`/`ht_free`/overwrite. Update the ownership contract in the header
   and add a test using heap-allocated string values — then prove no leaks with
   `make asan`.

5. **Open addressing variant.** Reimplement the same public API with
   **linear-probing open addressing** and tombstones instead of chaining
   (`hashtable_oa.c`). Run the *same* test suite against it (the header doesn't
   change). Compare load-factor behaviour and write up the trade-offs.

6. **Add a CMake build and a libFuzzer harness.** Do upgrade-path steps 2 and 4
   for real: a `CMakeLists.txt` with a `ctest` test, and a fuzz target that
   cross-checks the table against a simple sorted-array oracle under
   `-fsanitize=fuzzer,address`.
