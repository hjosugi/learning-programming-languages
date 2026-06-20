# Learning Programming Languages

Small runnable language labs for C, Rust, Zig, Haskell, Common Lisp, COBOL, ML from scratch, and Web3/blockchain basics.

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

Python-only projects:

```bash
python3 languages/ml/src/test_ml.py
python3 languages/web3/blockchain/test_chain.py
```

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
zig build test
```

Haskell:

```bash
cd languages/haskell
cabal test
```

Common Lisp:

```bash
cd languages/lisp
sbcl --script test/test.lisp
```

COBOL:

```bash
cd languages/cobol
./test.sh
```

## Directory Map

```text
languages/
  c/        # hashtable and memory ownership basics
  rust/     # typed CLI/store exercise
  zig/      # arrays, ring buffers, comptime-friendly basics
  haskell/  # pure functions and cabal project layout
  lisp/     # macros, conditions, packages, data modeling
  cobol/    # batch-style payroll processing
  ml/       # ML algorithms from scratch in Python
  web3/     # toy blockchain data model and validation
```

## What Belongs Elsewhere

- design patterns across languages belong in `learning-design-patterns-polyglot`
- build tooling experiments belong in `learning-build-systems`
- backend framework examples belong in `learning-backend-ddd`
- security labs belong in `learning-security-labs`
