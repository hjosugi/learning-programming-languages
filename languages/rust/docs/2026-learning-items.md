# 2026 Learning Items: Rust

Last verified: 2026-06-21

The named learning targets for this repo, each mapped to where the `kvstore`
hands-on exercises it.

## Must Learn

### Ownership & borrowing

- move semantics (values are moved, not copied, unless `Copy`)
- ownership transfer into and out of collections
- immutable borrows `&T` vs mutable borrows `&mut T`
- the borrow rules: many readers XOR one writer
- `clone` as an explicit, visible cost
- `Copy` vs `Clone`
- the `entry` API for get-or-insert mutation

Exercised in: `src/store.rs` (`HashMap<String, Value>`, `set` by value, `get`
by `&self`, `del`/`incr_by` by `&mut self`, `entry().or_insert()`).

Outcome:

- Explain why `set` takes `String`/`Value` by value but `get` takes `&str`.
- Explain what the borrow checker forbids while a `&mut self` borrow is alive.

### Lifetimes

- lifetime elision in method signatures
- returning references tied to `&self`
- explicit lifetime parameters on free functions (`fn f<'a>(..) -> &'a T`)
- why a returned reference cannot outlive its owner

Exercised in: `src/store.rs::get` (`Option<&Value>`), `src/command.rs::one_arg`
(`<'a>(.., args: &[&'a str]) -> Result<&'a str>`).

Outcome:

- Read an elided signature and state the implied lifetime.
- Explain why the `GET` outcome clones instead of borrowing.

### Traits & generics

- defining a custom trait
- implementing a trait for several types (incl. primitives)
- generic functions with trait bounds (`T: Encode`)
- `where` clauses and `IntoIterator`
- monomorphization / zero-cost abstraction
- `From`/`Into` conversions

Exercised in: `src/value.rs` (`Encode` trait; impls for `Value`, `i64`, `str`;
generic `encode_all<T, I>`; `From<i64>/From<&str>` for `Value`).

Outcome:

- Add a new `Encode` impl and call `encode_all` over it.
- Explain static dispatch (generics) vs dynamic dispatch (`&dyn Encode`).

### Enums + pattern matching

- data-carrying enum variants (sum types)
- exhaustive `match` (compiler-enforced)
- struct-variant and tuple-variant patterns
- slice patterns (`[a, rest @ ..]`, `[front @ .., last]`)
- `match` guards and binding
- `matches!` for boolean checks

Exercised in: `src/value.rs::Value`, `src/command.rs::Command` + `parse`,
`src/store.rs::execute`.

Outcome:

- Add an enum variant and let the compiler find every `match` to update.
- Use a slice pattern to parse an optional trailing flag.

### Result/Option error handling

- `Option<T>` for "maybe absent", `Result<T, E>` for "maybe failed"
- a custom error `enum` instead of stringly-typed errors
- implementing `Display` and `std::error::Error`
- `Error::source` for error chains
- the `?` operator and `From`-based error conversion
- `Box<dyn Error>` interop
- mapping errors to process exit codes

Exercised in: `src/error.rs` (`StoreError`, `ParseError`), used throughout;
`src/main.rs` (`ExitCode`).

Outcome:

- Add a new error variant with a helpful `Display` message.
- Explain why `From<ParseError> for StoreError` makes `?` ergonomic.

### Cargo tests/doctests

- `#[cfg(test)] mod tests` unit tests (can see private items)
- integration tests under `tests/` (public API only, separate crate)
- driving the compiled binary via `CARGO_BIN_EXE_<name>`
- doctests in `///` comments (compiled + run by `cargo test`)
- asserting on success *and* error cases
- `cargo clippy` / `cargo fmt` as quality gates

Exercised in: unit tests in every `src/` module, `tests/cli.rs`, doctests in
`src/lib.rs` and `src/command.rs`.

Outcome:

- Know which test kind sees private items and which sees only the public API.
- Add an error-case test and a doctest for a new command.

## Definition of Done

- `cargo run --manifest-path languages/rust/Cargo.toml` starts
  the REPL; one-shot mode works and exits non-zero on error.
- `cargo test --manifest-path languages/rust/Cargo.toml`
  passes with unit tests + at least one integration test + at least one doctest,
  covering multiple cases including error cases.
- `cargo clippy --all-targets` and `cargo fmt --check` are clean.
- The build uses std only (no `[dependencies]`) and works fully offline.
- Each named learning target above has at least one concrete location in the
  source and a passing test that exercises it.
- README documents Run, Test, Walkthrough, Upgrade path, and Exercises.

## Tradeoff Questions

Ask these as the project grows:

- Should this failure be a `Result` (caller can handle) or a `panic!`
  (programmer bug / unrecoverable)?
- Should this function take ownership, `&`, or `&mut`? What is the cheapest that
  still compiles?
- Is a `clone` here a real cost or noise? Could a borrow + lifetime avoid it?
- Generics (static dispatch, code bloat) or `dyn Trait` (dynamic dispatch,
  smaller binary)?
- Does adding a crate (`clap`, `serde`, `anyhow`) earn its keep, or does std
  suffice for the learning goal?
