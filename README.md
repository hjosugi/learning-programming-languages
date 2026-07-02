# Learning Programming Languages

Small runnable language labs for C, Rust, Zig, Haskell, Common Lisp, COBOL, ML from scratch, Web3/blockchain basics, and functional programming.

Last verified: 2026-06-21

## Why This Repo Exists

Language-specific learning repos were getting noisy as separate repositories. This repo keeps those exercises together while preserving one runnable project per topic.

Keep examples small:

- one clear language feature or runtime idea per directory
- source and tests close together
- generated outputs out of git
- toolchain-specific examples allowed, but the required command must be documented

## Hands-On Projects

If a language tool is missing locally, enter the Nix shell first:

```bash
nix develop
```

> **No Nix? Use mise.** On machines without Nix, `zig`, `ghc` / `runghc`,
> `cabal`, and `sbcl` are not on `PATH`. Prefix those commands with
> `mise exec --`, e.g. `mise exec -- zig build test` or
> `mise exec -- sbcl --script test/test.lisp`. `cargo` and `make` work directly.
> The per-language commands below already use the `mise exec --` form where it is
> needed.

C:

```bash
cd languages/c/hashtable
make test
```

Rust:

```bash
cd languages/rust
cargo test
```

Zig:

```bash
cd languages/zig
mise exec -- zig build test
```

Haskell (offline `runghc`; no package downloads):

```bash
cd languages/haskell
mise exec -- runghc -isrc app/Main.hs    # run the demo
mise exec -- runghc -isrc test/Spec.hs   # run the test suite
```

(The Nix / upgrade path uses `cabal test` instead; see `languages/haskell/README.md`.)

Common Lisp:

```bash
cd languages/lisp
mise exec -- sbcl --script test/test.lisp
```

COBOL:

```bash
cd languages/cobol
./test.sh
```

ML from scratch:

```bash
python3 languages/ml/src/test_ml.py
```

Web3 / toy blockchain:

```bash
python3 languages/web3/blockchain/test_chain.py
```

See `languages/web3/blockchain/README.md` for the package map and the
invariants that make the chain validation exercise useful.

Functional programming basics:

```bash
node topics/functional-programming-basics/result.test.mjs
```

PDF toolkit (from scratch, stdlib only):

```bash
cd topics/pdf-toolkit
python3 tests/test_pdftoolkit.py
python3 -m pdftoolkit info some.pdf   # reorder/select/rotate/merge/split/img2pdf/compress/note/highlight
python3 -m pdftoolkit serve --dir .   # tabbed browser viewer/editor (open files, notes, highlights, Drive)
```

See `topics/pdf-toolkit/README.md` for the full set of page operations, the
note/highlight annotations, the tabbed app, and how the PDF object graph is
parsed and rewritten without any third-party library.

## Directory Map

```text
languages/
  c/        # hashtable and memory ownership basics
  rust/     # typed CLI/store exercise
  zig/      # arrays, ring buffers, comptime-friendly basics
  haskell/  # pure functions, a tiny CLI shell, and cabal project layout
  lisp/     # macros, conditions, packages, data modeling
  cobol/    # batch-style payroll processing
  ml/       # ML algorithms from scratch in Python
  web3/     # toy blockchain data model and validation
topics/
  functional-programming-basics/
  pdf-toolkit/   # a from-scratch, stdlib-only PDF page toolkit (reorder/cut/merge/...)
```

## What Belongs Elsewhere

- design patterns across languages belong in `learning-design-patterns-polyglot`
- build tooling experiments belong in `learning-build-systems`
- backend framework examples belong in `learning-backend-ddd`
- security labs belong in `learning-security-labs`
