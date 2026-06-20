# Further learning resources

Canonical **primary sources** only — official sites, original essays, and the reference
docs for the libraries used. Each entry has a one-line note on why it's here. Deep links
are intentionally avoided; start at these roots.

Last verified: 2026-06-21

## Functional programming fundamentals

- **The Haskell language** — <https://www.haskell.org> —
  home of the language, reports, and documentation hub used for the Haskell examples.
- **The Typeclassopedia** — <https://wiki.haskell.org/Typeclassopedia> —
  the canonical map of Functor / Applicative / Monad / Foldable / Traversable and how the
  typeclasses relate.

## Type-level programming

- **TypeScript Handbook — Type Manipulation** —
  <https://www.typescriptlang.org/docs/handbook/2/types-from-types.html> —
  official reference for conditional, mapped, template-literal, and other types-from-types.

## FP design patterns (libraries)

- **fp-ts** — <https://gcanti.github.io/fp-ts/> —
  typed functional patterns in TypeScript (`Option`, `Either`, `Task`, typeclasses) as a
  reference encyclopaedia of the shapes.
- **Effect** — <https://effect.website> —
  the modern TypeScript effect system; the practical successor lineage for typed effects,
  error channels, and dependency injection as values.

## Functional DDD

- **Domain Modeling Made Functional — Scott Wlaschin** —
  <https://pragprog.com/titles/swdddf/domain-modeling-made-functional/> —
  the book that defines functional DDD: types as the spec, workflows as functions, events.
- **F# for Fun and Profit — Scott Wlaschin** — <https://fsharpforfunandprofit.com> —
  free companion essays: railway-oriented programming, designing with types, value objects.
- **"Parse, don't validate" — Alexis King** —
  <https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/> —
  the original essay arguing you should parse input into precise types at the boundary.

## Functional core & imperative shell

- **"Boundaries" / Functional Core, Imperative Shell — Gary Bernhardt** —
  <https://www.destroyallsoftware.com/screencasts> —
  the screencast series that named the pattern: a pure core wrapped by a thin I/O shell.
