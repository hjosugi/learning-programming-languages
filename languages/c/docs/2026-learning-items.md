# 2026 Learning Items: C

Last verified: 2026-06-21

The named learning targets for this repo, each mapped to where the hands-on
already exercises it (`hashtable/`) and what "done" looks like.

## Must Learn

### Pointers and memory management

- pointers, dereferencing, pointer arithmetic
- pointer-to-pointer (`T **`) and why it removes the `prev` variable
- the heap: `malloc` / `calloc` / `realloc` / `free`
- **ownership**: exactly one owner per allocation; borrowed vs owned pointers
- partial-failure cleanup (free what you already allocated on a later failure)
- `free(NULL)` is safe; mirror that in your own destructors
- dangling pointers, use-after-free, double-free, leaks

Outcome:

- Explain, for every allocation in `hashtable.c`, who owns it and who frees it.
- State the difference between the borrowed pointers from `ht_get`/`ht_keys`
  and the owned array `ht_keys` returns.

### Structs

- declaring and using `struct`; `typedef struct`
- storing data **by value** (the `long`) vs **by reference** (the key pointer)
- self-referential structs (`struct ht_entry { ... struct ht_entry *next; }`)
- heap-allocating structs and linking them into a list

Outcome:

- Draw the in-memory shape of the table: array of bucket heads → chains of
  `ht_entry` nodes → owned key strings.

### Header / implementation separation

- `.h` declares the API; `.c` defines it
- include guards (`#ifndef/#define/#endif`)
- `static` functions for internal (private) helpers
- documenting the contract (ownership, NULL behaviour) in the header

Outcome:

- A consumer can use the table by including only `hashtable.h` and linking the
  compiled `hashtable.c`.

### Hash table mechanics

- a string hash (FNV-1a) and why power-of-two capacity lets you mask not modulo
- separate chaining for collisions
- load factor and the grow + **rehash** policy
- O(1) average insert/get/remove; worst case is chain length

Outcome:

- Force a visible grow (the demo does) and confirm every key survives the
  rehash with the right value.

### Makefile build

- targets and prerequisites; `.PHONY`
- variables (`CC`, `CFLAGS`) and overriding them (`make CC=clang`)
- order-only prerequisites (`| bin`) for the output directory
- the strict flag set: `-Wall -Wextra -Werror -std=c17`

Outcome:

- `all`, `run`, `test`, `asan`, `clean` all work and `test`/`asan` exit
  non-zero on failure.

### Testing and sanitizers

- `assert()` and that it compiles out under `-DNDEBUG` (so don't define it)
- a tiny `{name, fn}` runner; a failed assert → `abort()` → non-zero exit
- multiple cases: insert, get, overwrite, grow, remove, edge cases, NULL
- AddressSanitizer + UBSan (`-fsanitize=address,undefined`) with leak detection
- Valgrind as a second, independent check (upgrade path)

Outcome:

- The suite has many independent cases, all green, and is clean under
  `make asan`.

## Definition of Done

- [x] Hash table with `hashtable.h` + `hashtable.c` + demo `main.c`.
- [x] Manual `malloc`/`free` with a documented ownership contract; no leaks.
- [x] Pointers (incl. pointer-to-pointer unlink) and structs exercised.
- [x] Defensive NULL handling on every public function, tested.
- [x] `assert()`-based test runner with multiple cases (insert/get/grow/remove/
      edge/NULL).
- [x] Makefile with `all`, `test` (non-zero on failure), `asan`, `clean` using
      `-Wall -Wextra -Werror -std=c17`.
- [x] Clean under AddressSanitizer + UBSan with leak detection.
- [x] Builds with both `gcc` and `clang`, offline.
- [x] README with Run / Test / Walkthrough / Upgrade path / Exercises and a
      "Last verified" date.
