# Learning Haskell

A thorough (てあつく) GHC hands-on built around one small, idiomatic program: an
**arithmetic expression parser + evaluator**. It is deliberately written to
exercise the *signature features* of Haskell, one concept at a time, with
meaningful comments and a real passing test suite.

- Toolchain: **GHC 8.10.7** (`runghc` / `ghc`), **base library only**, fully **offline**.
- No hackage / cabal downloads are needed for the primary workflow.

Last verified: 2026-06-21

## What it demonstrates (the named learning targets)

| Learning target | Where to look |
| --- | --- |
| Purity & IO separation | `app/Main.hs` is the *only* file that does IO; `src/Calc.hs` is 100% pure |
| Algebraic data types | `Expr`, `Op`, `Token`, `CalcError`, and the `Parser` newtype in `src/Calc.hs` |
| Pattern matching | every function deconstructs constructors (`eval`, `apply`, `pretty`, `tokenize`) |
| Typeclass (defined by us) | `class Pretty` + instances for `Op`, `Expr`, `CalcError` |
| Maybe / Either | `readDouble :: Maybe`, the whole pipeline returns `Either CalcError a` (no `error`/`head`/`read`) |
| Recursion + higher-order functions | recursive `tokenize`, recursive-descent parser, `map`/`foldl'` in `runAll`/`countOk` |
| Functor / Applicative / Monad intuition | the `Parser` newtype implements all three (and `Alternative`) **by hand** |

## How this repo is organized

```text
learning-haskell/
  src/Calc.hs          -- the pure library: lexer + parser + evaluator + Pretty
  app/Main.hs          -- the only IO; reads argv or runs a demo, prints, exits
  test/Spec.hs         -- base-only test runner (hand-rolled asserts; exit!=0 on fail)
  learning-haskell.cabal  -- the UPGRADE PATH (cabal build/test); not needed for runghc
  mise.toml            -- pins GHC 8.10.7 and puts ./toolchain on PATH (see "Toolchain note")
  toolchain/           -- tiny shims so GHC finds a working C compiler on this machine
  docs/
    2026-learning-items.md   -- named learning targets + Definition of Done
    learning-resources.md    -- curated canonical primary sources
```

The hands-on *is* the repo root, so this README carries the Run / Test /
Walkthrough / Upgrade path / Exercises sections below.

## Run

Copy-pasteable, absolute paths, works from any directory:

```bash
# Run the built-in demo (success + every error kind):
mise exec --cd languages/haskell -- runghc -ilanguages/haskell/src languages/haskell/app/Main.hs

# Evaluate your own expression (exits non-zero on a parse/eval error):
mise exec --cd languages/haskell -- runghc -ilanguages/haskell/src languages/haskell/app/Main.hs "2 ^ 3 ^ 2"
```

If you are already `cd`'d into the repo, the short form also works:

```bash
mise exec -- runghc -isrc app/Main.hs
mise exec -- runghc -isrc app/Main.hs "1 + 2 * 3"
```

Expected demo output:

```text
Calc -- arithmetic expression evaluator
---------------------------------------
  1 + 2 * 3  =>  7
  (1 + 2) * 3  =>  9
  2 ^ 3 ^ 2  =>  512
  -3 + 4  =>  1
  10 / 4  =>  2.5
  10 / (5 - 5)  =>  evaluation error: division by zero
  1 +   =>  parse error: trailing tokens: [TOp Add]
  1 + $  =>  lex error: unexpected character: $
```

## Test

Non-interactive; prints PASS/FAIL per case and exits non-zero if any check fails:

```bash
mise exec --cd languages/haskell -- runghc -ilanguages/haskell/src languages/haskell/test/Spec.hs
```

Short form when inside the repo:

```bash
mise exec -- runghc -isrc test/Spec.hs
```

There are 33 assertions covering tokenizing, AST shape (precedence /
associativity / unary minus / parens), numeric evaluation, every typed error
(`DivByZero`, `ParseError`, `LexError`), the `Pretty` instances, a pretty →
re-parse round trip, the `Parser` Functor/Applicative instances, and the
`runAll`/`countOk` higher-order helpers.

## Toolchain note (why `mise.toml` + `toolchain/` exist)

The GHC 8.10.7 installed via mise on this machine was configured to use a conda
C toolchain (`x86_64-conda-linux-gnu-gcc` etc.) that is **not present** here.
GHC needs a C compiler even to *run* code with `runghc`. Rather than edit GHC's
global `settings`, this repo ships four one-line shim scripts in `./toolchain/`
that forward those conda tool names to the system `gcc` / `ld` / `ar` /
`ranlib`, and `mise.toml` puts `./toolchain` on `PATH` for anything launched via
`mise exec --` (that is why the Run/Test commands include `--cd <repo>` so mise
discovers this config from any directory). On a machine whose GHC already points
at a valid toolchain, the shims simply forward to the same compilers and nothing
changes.

## Upgrade path

This repo intentionally stays on `runghc` + `base` so it runs offline. When you
have a package set, grow it like this:

1. **Real project tooling.** `cabal build` / `cabal run calc` / `cabal test`
   using the included `learning-haskell.cabal` (incremental compilation, proper
   module graph). Or generate a `stack.yaml` and use `stack build && stack test`.
2. **Property-based + spec testing.** Replace the hand-rolled `test/Spec.hs`
   with **Hspec** (`describe`/`it`) for structure and **QuickCheck** for
   properties — e.g. *"for any `Expr`, `parse (lexer (pretty e))` evaluates to
   the same value as `eval e`"*, with a `Gen Expr`/`Arbitrary` instance.
3. **Lean into the typeclass hierarchy.** Derive `Functor`/`Foldable`/`Traversable`
   for a generalized `ExprF` and refactor the evaluator as a fold (recursion
   schemes / `cata`). Make the lexer's `Either` plumbing explicit via
   `ExceptT`/`StateT` and study the laws (Functor/Applicative/Monad) you are
   relying on.
4. **Parser combinators for real.** Swap the hand-rolled `Parser` newtype for
   **megaparsec** (or `parsec`/`attoparsec`): better error messages, source
   positions, `try`/`<?>`, and built-in `chainl1`/`makeExprParser`.
5. **Stricter language edition.** Turn on **GHC2021** (or move to GHC 9.x) and
   enable extensions like `LambdaCase`, `DerivingStrategies`,
   `GeneralizedNewtypeDeriving`, and `-Wall -Werror`. Add **HLint** and
   **fourmolu/ormolu** formatting to CI.

## Walkthrough

The program is a textbook three-stage pipeline, kept pure end to end:

```
String --tokenize--> [Token] --parse--> Expr --eval--> Double
   (Either CalcError at every arrow; a Left short-circuits the rest)
```

- **Algebraic data types.** `Expr` is a *recursive sum type* — `Num`, `Neg`,
  `BinOp` — so a value of type `Expr` literally *is* a syntax tree. `Op`,
  `Token`, and `CalcError` are smaller sum types. This is the core Haskell idea:
  model the domain as data, then write total functions over it.
- **Pattern matching.** Every consumer (`eval`, `apply`, `pretty`, `tokenize`)
  matches on constructors. The compiler checks the matches are exhaustive, so an
  unhandled case is a *compile-time* error, not a crash.
- **A typeclass we define.** `class Pretty a where pretty :: a -> String`, with
  instances for `Op`, `Expr`, and `CalcError`. Defining our own class (instead
  of reusing `Show`) is the lesson: ad-hoc polymorphism via instances.
- **Maybe / Either for errors.** There are *no partial functions* for expected
  failures: `readDouble` returns `Maybe Double` by pattern-matching on `reads`
  (never `read`), and the pipeline returns `Either CalcError a`. The final
  `tokenize input >>= parse >>= eval` is `Either`'s monad doing the error
  plumbing — each stage runs only if the previous produced a `Right`.
- **Recursion + higher-order functions.** `tokenize` is direct recursion over
  the character list (with `span`, a HOF, to grab number runs). The parser is
  recursive descent. `chainl1` is a higher-order combinator that takes an
  *operator parser* as an argument. `runAll = map (...)` and
  `countOk = foldl' (...)` complete the map/fold pair.
- **Functor / Applicative / Monad intuition.** The `Parser a` newtype wraps
  `[Token] -> Either CalcError (a, [Token])`. We implement `Functor` (map the
  result), `Applicative` (`pure` consumes nothing; `<*>` threads the stream),
  `Monad` (`>>=` lets the next parser depend on the last result — enabling `do`
  notation in `factorP`/`baseP`), and `Alternative` (`<|>` = ordered choice).
  Building these by hand is the fastest way to *feel* what those classes mean.
- **Purity & IO separation.** `src/Calc.hs` mentions `IO` nowhere. All effects
  live in `app/Main.hs`, which only reads argv, calls the pure `runCalc`, prints,
  and chooses an exit code. The pure core is therefore trivially testable.

## Exercises

Progressive — each builds on the previous:

1. **Modulo operator.** Add `Mod` to `Op`, the `%` token to `tokenize`, a parser
   alternative at `term` precedence, and an `apply Mod` case that returns
   `Left DivByZero` on a zero divisor. Add tests for both the result and the
   error.
2. **Named constants.** Extend the lexer/parser to recognize the identifiers
   `pi` and `e`, producing `Num pi` / `Num (exp 1)`. Add a round-trip test.
3. **A new typed error.** Introduce `UnknownName String` to `CalcError`, then add
   variables (`let x = 3 in x * x` *or* a simple environment passed to `eval`)
   and return that error for an unbound name. Render it in the `Pretty CalcError`
   instance.
4. **Functions.** Support unary functions `sqrt`, `sin`, `cos`, `abs` as
   `Call String Expr` in the AST. Watch how one new constructor forces you to
   handle it in `eval` *and* `pretty` (exhaustiveness keeping you honest).
5. **A property test, by hand.** Without adding any dependency, write a generator
   of random `Expr` values and assert that `parse (lex (pretty e))` evaluates to
   the same number as `eval e` for a few hundred cases (mind floating-point
   tolerance). This previews QuickCheck's `Arbitrary`.
6. **Switch to megaparsec (upgrade path).** Once you can install packages,
   reimplement `parse` with `Text.Megaparsec` and `Control.Monad.Combinators.Expr`
   (`makeExprParser`), and compare the error messages with the hand-rolled
   version.

## References

- The Haskell language site: https://www.haskell.org
- Curated primary sources: [docs/learning-resources.md](docs/learning-resources.md)
- Named learning targets + Definition of Done: [docs/2026-learning-items.md](docs/2026-learning-items.md)
