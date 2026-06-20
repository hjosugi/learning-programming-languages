# Learning Rust

A rigorous, std-only hands-on for learning Rust's signature features through one
small but real program: a **typed in-memory key/value store with a command
parser** (`kvstore`).

Last verified: 2026-06-21

This repo is a single Cargo project. The library (`src/`) and a small REPL
binary (`src/main.rs`) together exercise every named learning target:

| Learning target | Where it lives |
| --- | --- |
| Ownership & borrowing | `src/store.rs` — owning `HashMap<String, Value>`, `&self` reads vs `&mut self` writes |
| Lifetimes | `src/store.rs::get` returns `Option<&Value>`; `one_arg<'a>` in `src/command.rs` |
| Traits & generics | `src/value.rs` — the `Encode` trait + generic `encode_all<T: Encode, I>` |
| Enums + pattern matching | `src/value.rs::Value`, `src/command.rs::Command`, every `match` |
| Result/Option error handling | `src/error.rs` — custom `StoreError`/`ParseError` enums (`Display` + `std::error::Error`) |
| Cargo tests/doctests | `#[cfg(test)] mod` in each module, `tests/cli.rs`, doctests in `///` comments |

## How this repo is organized

```text
learning-rust/
  Cargo.toml                 # manifest — NO external deps, builds offline
  src/
    lib.rs                   # crate root + module wiring + an end-to-end doctest
    error.rs                 # StoreError / ParseError (custom Error enum)
    value.rs                 # Value enum + Encode trait + generic encode_all
    command.rs               # Command enum + the parse() function (+ doctest)
    store.rs                 # Store (HashMap) + execute() + Outcome
    main.rs                  # REPL / one-shot CLI binary
  tests/
    cli.rs                   # integration tests (public API + the compiled binary)
  docs/
    2026-learning-items.md   # named learning targets + Definition of Done
    learning-resources.md    # canonical primary sources
```

The hands-on **is** this repo root; this README is the hands-on's README.

## Run

The store works in two modes. Interactive REPL:

```bash
cargo run --manifest-path languages/rust/Cargo.toml
```

Then type commands (Ctrl-D or `quit` to exit):

```text
> SET name alice
OK
> SET visits 0
OK
> INCRBY visits 7
7
> GET visits
7
> TYPE name
text
> KEYS
name
visits
```

One-shot mode (the trailing args become a single command; exits non-zero on error):

```bash
cargo run --manifest-path languages/rust/Cargo.toml -- SET greeting hello
cargo run --manifest-path languages/rust/Cargo.toml -- INCRBY counter 5
```

## Test

Runs unit tests, the integration test, and the doctests — non-interactive,
exits non-zero on any failure:

```bash
cargo test --manifest-path languages/rust/Cargo.toml
```

Expected: `19` unit tests, `5` integration tests, `2` doctests — all passing.

Optional quality gates (also clean):

```bash
cargo clippy --manifest-path languages/rust/Cargo.toml --all-targets
cargo fmt    --manifest-path languages/rust/Cargo.toml --check
```

## Walkthrough

The whole program is one pipeline:

```text
"INCRBY visits 7"  --parse-->  Command::IncrBy { key, amount }
                   --execute->  Outcome::Int(7)
                   --render-->  "7"
```

Reading the modules in this order tracks the Rust concepts:

1. **`error.rs` — errors are values.** `StoreError` is a closed `enum`. Every
   fallible function returns `Result<T, StoreError>`. There are no exceptions
   and no `null`; absence is `Option`, failure is `Err`. `StoreError` implements
   `Display` *and* `std::error::Error` (with `source()` exposing the wrapped
   `ParseError`), so it drops straight into `Box<dyn Error>`. The
   `From<ParseError> for StoreError` impl is what makes the `?` operator convert
   parse errors automatically.

2. **`value.rs` — enums, a custom trait, and generics.** `Value` is an `enum`
   with data-carrying variants (`Int`, `Text`, `List`) — a sum type. `Encode` is
   *our own* trait (not just `Display`); implementing it for `Value`, `i64`, and
   `str` lets the generic `encode_all<T: Encode, I: IntoIterator<Item = T>>`
   work over any of them. Generics here are **monomorphized**: the compiler
   stamps out a specialized copy per concrete type, so the abstraction is
   zero-cost.

3. **`command.rs` — pattern matching does the parsing.** `parse` tokenizes a
   line and uses **slice patterns** (`[verb, rest @ ..]`, `[front @ .., "--nx"]`)
   plus a `match` on the verb to build a typed `Command`. Illegal commands are
   unrepresentable: you cannot construct a `Command::Get` without a key. Arity
   and integer-validation failures become typed `ParseError`s, not panics.

4. **`store.rs` — ownership & borrowing, made concrete.**
   - The store **owns** its data: `HashMap<String, Value>`. `set` takes the key
     and value **by value**, so ownership *moves* into the map.
   - `get(&self, ..) -> Option<&Value>` borrows **immutably** and hands back a
     reference *into* the map. The (elided) lifetime ties that reference to the
     `&self` borrow, so the borrow checker guarantees it can never dangle.
   - `del`/`incr_by`/`set` take `&mut self`. While a `&mut` borrow is alive, Rust
     statically forbids any other reference — that is the data-race-freedom
     guarantee, enforced at compile time.
   - **clone vs borrow:** `execute` returns an owned `Outcome`. For `GET` it
     `clone`s the value so the result can outlive the `&self` borrow. That clone
     is a deliberate, visible cost — the alternative (returning a borrow) would
     tie `Outcome`'s lifetime to the store and is left as an exercise.

5. **`main.rs` — composition with the outside world.** `main` returns
   `ExitCode`; the REPL keeps one long-lived `Store` across many commands;
   `and_then(|cmd| store.execute(cmd))` chains the parse and execute `Result`s.

### Tests, three layers

- **Unit tests** (`#[cfg(test)] mod tests` in each `src/` file) can see private
  items and cover success *and* error paths case by case.
- **Integration test** (`tests/cli.rs`) is compiled as a *separate crate*, so it
  only sees the public API — and it also launches the compiled binary via
  `CARGO_BIN_EXE_kvstore` to assert real exit codes and stderr.
- **Doctests** (the ```` ``` ```` blocks in `src/lib.rs` and `src/command.rs`)
  are compiled and run by `cargo test`, so the documentation can never drift
  from the code.

## Upgrade path

This is intentionally std-only. Grow it toward production tooling step by step:

1. **CLI args with `clap`** — replace the hand-rolled arg join in `main.rs` with
   `clap` derive for subcommands, `--help`, and flag parsing.
2. **Serialization with `serde`** — derive `Serialize`/`Deserialize` on `Value`
   and add `SAVE`/`LOAD` commands that persist the store as JSON.
3. **Error ergonomics with `anyhow`/`thiserror`** — keep `StoreError` as the
   library's typed error (swap the hand-written impls for `thiserror`), and use
   `anyhow::Result` at the binary boundary.
4. **More modules** — split `command.rs` into a tokenizer + parser; add a
   `wal.rs` write-ahead log module.
5. **A Cargo workspace** — promote to a workspace with `crates/kvstore-core`,
   `crates/kvstore-cli`, and a `crates/kvstore-bench` using `criterion`.
6. **Concurrency / async** — wrap the store in `Arc<Mutex<Store>>` or an
   `RwLock`, then expose it over a `tokio` TCP server speaking the same command
   protocol (a mini RESP).

Each step is additive; the core library API stays the same.

## Exercises

Progressive, each builds on the last. After each, run
`cargo test --manifest-path languages/rust/Cargo.toml`.

1. **Add `EXISTS key`** returning `Outcome::Int(0|1)`. Wire it through the
   `Command` enum, `parse`, and `execute`. Add a unit test for present and
   absent keys. (Practices: enum extension, exhaustive `match`.)
2. **Add `APPEND key text`** that appends to a `Value::Text` and errors with a
   new `StoreError` variant when the value is an `Int`/`List`. Add the error
   case to `tests/cli.rs`. (Practices: custom error variant, `&mut` mutation.)
3. **Add `DECRBY key amount`** by reusing `incr_by` with a negated amount, and
   guard against `i64` overflow with a typed error instead of `saturating_add`.
   (Practices: `Result`, integer-overflow handling.)
4. **Make `get` zero-copy at the edge.** Add a method
   `get_ref(&self, key) -> Result<&Value>` and an `Outcome` variant that borrows,
   parameterized by a lifetime, then explain in a comment why `execute`’s
   current owned `Outcome` is easier to use. (Practices: explicit lifetimes,
   clone-vs-borrow tradeoff.)
5. **Generalize `Encode` into encode + decode.** Add a `Decode` trait and a
   generic `round_trip<T: Encode + Decode>(value: T) -> bool` helper with a
   property-style test over several values. (Practices: trait bounds, generics.)
6. **Persist the store.** Add `SAVE path` / `LOAD path` using only `std::fs`
   and your `Encode`/`Decode` traits (no serde yet), with an integration test
   that round-trips through a temp file. (Practices: `Result` + `?` with I/O
   errors, `From` conversions for a new `StoreError::Io` variant.)

## Learning targets and resources

- Named learning targets and Definition of Done: [docs/2026-learning-items.md](docs/2026-learning-items.md)
- Canonical primary sources: [docs/learning-resources.md](docs/learning-resources.md)
