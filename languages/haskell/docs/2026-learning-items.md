# 2026 Learning Items: Haskell (GHC)

Last verified: 2026-06-21

The named targets for this repo, grouped as "must learn" with concrete
sub-topics. The hands-on (`src/Calc.hs` + `app/Main.hs` + `test/Spec.hs`) is the
proving ground for all of them.

## Must Learn

### Purity & IO separation

- pure functions: same input → same output, no effects
- `IO a` as a *value* describing an effect, not a side effect that "just happens"
- keeping the core pure and pushing IO to the edges (`Main`)
- `getArgs`, `putStrLn`, `mapM_`, `exitSuccess`/`exitFailure`
- why a pure core is trivially testable

Outcome:

- State, for any function in `Calc`, why it can never perform IO.
- Explain how `Main` is the only place effects occur.

### Algebraic data types

- sum types (multiple constructors): `Op`, `Token`, `CalcError`
- product / record-ish constructors with fields: `BinOp Op Expr Expr`
- *recursive* data types: `Expr` as a syntax tree
- `newtype` vs `data`: the `Parser` newtype
- `deriving (Eq, Show)`

Outcome:

- Model a small domain as data first, functions second.
- Read a recursive type and see the tree it describes.

### Pattern matching

- matching on constructors in function equations
- nested patterns, wildcards `_`, as-patterns
- guards (`|`) and pattern guards (`| Just op <- lookup ...`)
- `case ... of`
- exhaustiveness: the compiler catches missed cases

Outcome:

- Write total functions over an ADT with no partial cases.
- Use `-Wall` to surface non-exhaustive matches.

### Typeclasses

- declaring a class: `class Pretty a where pretty :: a -> String`
- writing instances for several types
- the difference between `Show` (debugging) and a domain class like `Pretty`
- standard classes touched here: `Eq`, `Show`, `Functor`, `Applicative`,
  `Monad`, `Alternative`

Outcome:

- Define a class and at least two instances.
- Explain ad-hoc polymorphism (instances) vs parametric polymorphism (generics).

### Maybe / Either for error handling

- `Maybe a` for "value or nothing" (`readDouble`)
- `Either e a` for "value or a typed error" (`CalcError`)
- avoiding partial functions for expected errors (no `head`, `fromJust`, `read`,
  `error`)
- short-circuiting with `>>=` / `do` in `Either`
- `fmap`/`<$>` over `Either`

Outcome:

- Replace every "this can fail" path with a value, not an exception.
- Chain fallible stages so the first failure wins.

### Recursion & higher-order functions

- direct recursion over lists (`tokenize`)
- recursive descent (the parser mirrors the grammar)
- `map`, `foldl'`, `span`, function composition `.`
- functions that take functions: `chainl1`, `satisfy`

Outcome:

- Write a recursive function with a clear base case.
- Use `map`/`fold` instead of manual loops; pass behavior as an argument.

### Functor / Applicative / Monad intuition

- `Functor`: `fmap` transforms a result inside a context
- `Applicative`: `pure` injects; `<*>` combines independent effects
- `Monad`: `>>=` sequences dependent effects; `do` notation
- `Alternative`: `empty` / `<|>` for choice
- all four implemented by hand on the `Parser` newtype
- the same intuition reused via `Either`'s instances in the pipeline

Outcome:

- Implement `Functor`/`Applicative`/`Monad` for a custom type.
- Explain what changes as you move Functor → Applicative → Monad (independent vs
  dependent steps).

## Definition of Done

- `src/Calc.hs` compiles clean under `-Wall` (no warnings).
- The demo runs: `mise exec -- runghc -isrc app/Main.hs` prints success *and*
  every error kind.
- The test suite passes and is non-interactive: `mise exec -- runghc -isrc
  test/Spec.hs` exits 0 with all cases PASS, and exits non-zero if any fails.
- The code uses **no partial functions** for expected errors (no `head`,
  `fromJust`, `read`, `error`); every recoverable failure is a `Maybe`/`Either`
  value.
- The repo exercises every "Must Learn" target above, each findable from the
  table in `README.md`.
- A learner can name, for any function, whether it is pure and why.
- The Upgrade path (cabal/stack, Hspec/QuickCheck, recursion schemes,
  megaparsec, GHC2021) is documented and at least one step is attemptable.
