# Further learning resources

Last verified: 2026-06-21

Curated, canonical primary sources for this repo's named learning targets:
Rust ownership/borrowing, lifetimes, traits & generics, enums + pattern
matching, `Result`/`Option` error handling, and Cargo tests/doctests. Prefer
these official docs and well-known books over blog posts; they are the reference
line this repo follows. All URLs are canonical roots under `doc.rust-lang.org`,
`rust-lang.org`, or `crates.io`.

## Start here

- **The Rust Programming Language ("the book")** — https://doc.rust-lang.org/book/
  The official introductory book. Chapter 4 (ownership), 10 (generics, traits,
  lifetimes), 6 (enums + `match`), and 9 (error handling) map directly onto every
  module in this repo.

- **Rust by Example** — https://doc.rust-lang.org/rust-by-example/
  Runnable, example-first companion to the book. Best for quickly seeing the
  syntax for `match`, traits, generics, and `Result`/`Option`.

## Ownership, borrowing, and lifetimes

- **The book — Understanding Ownership** — https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
  Moves, borrows, and the rules the borrow checker enforces — the foundation for
  `src/store.rs`.

- **The book — Validating References with Lifetimes** — https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html
  Lifetime elision and explicit lifetime parameters; explains the signatures of
  `Store::get` and `command::one_arg`.

- **The Rustonomicon** — https://doc.rust-lang.org/nomicon/
  Deeper, "how it really works" reference for ownership, lifetimes, and
  subtyping. Read after the book when you want the model behind the rules.

## Traits and generics

- **The book — Generic Types, Traits, and Lifetimes** — https://doc.rust-lang.org/book/ch10-00-generics.html
  Defining traits, implementing them, and bounding generics — the model behind
  `Encode` and `encode_all`.

- **The Rust Reference — Traits** — https://doc.rust-lang.org/reference/items/traits.html
  The language reference for trait definitions, object safety, and dispatch;
  the precise rules behind static vs `dyn` dispatch.

## Enums and pattern matching

- **The book — Enums and Pattern Matching** — https://doc.rust-lang.org/book/ch06-00-enums.html
  Data-carrying variants and exhaustive `match`; the model behind `Value` and
  `Command`.

- **The Rust Reference — Patterns** — https://doc.rust-lang.org/reference/patterns.html
  The full pattern grammar, including the slice patterns (`[a, rest @ ..]`,
  `[front @ .., last]`) used in `command::parse`.

## Error handling: Result, Option, and custom errors

- **The book — Error Handling** — https://doc.rust-lang.org/book/ch09-00-error-handling.html
  `panic!` vs `Result`, the `?` operator, and when to use each — the model
  behind `StoreError` and `main`'s `ExitCode`.

- **std::error::Error** — https://doc.rust-lang.org/std/error/trait.Error.html
  The trait this repo implements on `StoreError`/`ParseError`, including
  `source()` for error chains.

- **std::result / std::option** — https://doc.rust-lang.org/std/result/ ,
  https://doc.rust-lang.org/std/option/
  The combinator methods (`map`, `and_then`, `ok_or`, `map_err`) the code leans
  on instead of manual branching.

## Cargo, testing, and doctests

- **The Cargo Book** — https://doc.rust-lang.org/cargo/
  Canonical reference for `Cargo.toml`, `[lib]`/`[[bin]]`, profiles, and the
  `cargo test`/`cargo run` commands this repo documents.

- **The book — Writing Automated Tests** — https://doc.rust-lang.org/book/ch11-00-testing.html
  `#[test]`, `#[cfg(test)]` unit tests, and integration tests under `tests/`.

- **rustdoc — Documentation tests** — https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
  How the ```` ``` ```` blocks in `///` comments become compiled, executed tests.

## Idiom and API design

- **Rust API Guidelines** — https://rust-lang.github.io/api-guidelines/
  Official checklist for idiomatic public APIs (naming, conversions, error
  types) — the standard this repo's library API aims at.

- **Clippy lints index** — https://rust-lang.github.io/rust-clippy/
  The lint catalog behind `cargo clippy`; explains *why* each suggestion is more
  idiomatic.

## Tooling reference

- **Rust standard library docs** — https://doc.rust-lang.org/std/
  The full std reference (`HashMap`, `Vec`, `String`, `io`, `process::ExitCode`),
  all of which this std-only project uses.

- **crates.io** — https://crates.io
  Where the upgrade-path crates (`clap`, `serde`, `anyhow`, `thiserror`,
  `tokio`, `criterion`) live when you are ready to add dependencies.
