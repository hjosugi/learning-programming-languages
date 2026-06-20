# Further learning resources

Last verified: 2026-06-21

Curated, canonical primary sources for this repo's named learning targets:
Haskell purity & IO, algebraic data types, pattern matching, typeclasses,
Maybe/Either, recursion & higher-order functions, and the
Functor/Applicative/Monad hierarchy. Prefer these over blog posts; they are the
reference line this repo follows. URLs are canonical roots.

## Language home and official references

- **The Haskell language site** — https://www.haskell.org
  Official home: downloads (GHC), documentation hub, and community links. The
  starting point for everything below.

- **GHC User's Guide** — https://downloads.haskell.org/ghc/latest/docs/users_guide/
  The compiler's official manual: language extensions, warnings (`-Wall`),
  flags, and the `runghc`/`ghc` tooling this repo drives.

- **The Haskell 2010 Report** — https://www.haskell.org/onlinereport/haskell2010/
  The language standard. Authoritative on syntax, data declarations, pattern
  matching semantics, and the standard Prelude classes — i.e. the bedrock for
  ADTs, typeclasses, and `Either`/`Maybe`.

- **Hoogle (API search)** — https://hoogle.haskell.org
  Search functions by name *or type signature*. The fastest way to find what a
  combinator does and which typeclass it comes from.

- **Hackage: the `base` package** — https://hackage.haskell.org/package/base
  Reference docs for the only library this repo uses: `Data.Maybe`,
  `Data.Either`, `Data.List` (`foldl'`), `Control.Applicative` (`Alternative`),
  `System.Exit`, etc.

## Books (free, canonical)

- **Learn You a Haskell for Great Good!** — http://learnyouahaskell.com
  The classic gentle introduction; its chapters on types/typeclasses, recursion,
  higher-order functions, and "Functors, Applicative Functors and Monoids" map
  directly onto this repo's targets.

- **Real World Haskell (O'Reilly, free online)** — http://book.realworldhaskell.org
  A practical, project-driven book. Its parsing and error-handling chapters
  mirror the lexer/parser/`Either` design used here.

- **Programming in Haskell, Graham Hutton (book site)** — https://www.cs.nott.ac.uk/~pszgmh/pih.html
  A rigorous, concise textbook. Chapter on *functional parsers* is essentially
  the hand-rolled `Parser` newtype (Functor/Applicative/Monad) in this repo.

## Typeclass hierarchy (the Functor/Applicative/Monad target)

- **Typeclassopedia (Haskell Wiki)** — https://wiki.haskell.org/Typeclassopedia
  The canonical map of the standard typeclass hierarchy
  (Functor → Applicative → Monad, Foldable, Traversable, Alternative) with laws
  and intuition. The single best reference for this repo's hardest target.

- **Haskell Wiki** — https://wiki.haskell.org
  Community-maintained but canonical for idioms, the "monad tutorial" landscape,
  and "How to avoid partial functions" guidance behind the no-`head`/`read` rule.

## Upgrade-path tooling

- **Cabal user guide** — https://cabal.readthedocs.io
  The official build tool referenced by `learning-haskell.cabal`; how to
  `cabal build` / `cabal test` once you have a package set.

- **The Haskell Tool Stack** — https://docs.haskellstack.org
  Alternative build tool with curated, reproducible snapshots — the other route
  for the upgrade path.

- **Hspec** — https://hspec.github.io
  The spec-style testing framework to replace the hand-rolled `test/Spec.hs`.

- **QuickCheck** — https://hackage.haskell.org/package/QuickCheck
  Property-based testing: generate random `Expr` values and check round-trip
  laws, the natural next step after the example-based tests here.

- **megaparsec** — https://hackage.haskell.org/package/megaparsec
  Production parser-combinator library (with `makeExprParser`) to replace the
  hand-rolled parser in the upgrade path.
