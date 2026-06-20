# 2026 Learning Items — Functional Programming & Type-Level Programming

A focused checklist for the topics under [`../topics/`](../topics). Each item should end
up demonstrated by code that **compiles** (Haskell via `runghc`, TypeScript via the
documented `tsc`) and, where it makes sense, **runs** (`runghc` / `node file.ts`).
Negative cases ("this must NOT compile") are pinned with `// @ts-expect-error` in
TypeScript.

Last verified: 2026-06-21

## Must Learn — Functional programming fundamentals

- [ ] **Pure functions & referential transparency** — no hidden I/O or mutation; same
      input → same output; reason by substitution.
- [ ] **Immutability** — persistent data and copy-on-write updates instead of in-place
      mutation.
- [ ] **Totality** — prefer total functions; handle every case; avoid partial functions
      (`head`, unguarded division) and unchecked exceptions.
- [ ] **Algebraic data types** — model with sum types (`|` / `data ... | ...`) and
      product types (records/tuples); pattern-match exhaustively.
- [ ] **Higher-order functions & composition** — `map`/`filter`/`fold`, currying, partial
      application, `(.)` / pipe.
- [ ] **Recursion & folds** — structural recursion, `foldr`/`foldl`, and recognising the
      catamorphism behind a fold.
- [ ] **Functor / Applicative / Monad** — the everyday vocabulary: `map`, `pure`/`of`,
      `ap`, `flatMap`/`>>=`; the laws at an intuitive level.
- [ ] **Effects as values** — represent effects (`IO`, `Task`/`Promise`-as-data) as
      descriptions so the core stays pure.

## Must Learn — Type-level programming

### Haskell

- [ ] **GADTs** — type-indexed constructors that refine the result type
      (e.g. a well-typed expression `Expr a`), enabling exhaustive, type-safe `eval`.
- [ ] **TypeFamilies** — type-level functions; associated types on classes; computing
      types from types.
- [ ] **DataKinds** — promote values/constructors to the type level; kind-indexed types,
      type-level naturals/symbols, and phantom tags backed by real kinds.
- [ ] Combine the three: e.g. length-indexed vectors or state-machine-typed APIs where
      illegal transitions don't type-check.

### TypeScript

- [ ] **Conditional types** — `T extends U ? X : Y`, `infer`, distribution over unions.
- [ ] **Mapped types** — `{ [K in keyof T]: ... }`, key remapping with `as`, modifiers
      (`readonly`, `?`, `-`).
- [ ] **Template-literal types** — string-literal computation, pattern inference, building
      keys/routes at the type level.
- [ ] **Branded / nominal types** — `type Email = string & { readonly __brand: 'Email' }`
      so a raw `string` cannot stand in for a validated value.

## Must Learn — FP design patterns

- [ ] **Option / Maybe** — model absence without `null`; chain with `map`/`flatMap`.
- [ ] **Either / Result** — typed failures over exceptions; short-circuiting pipelines;
      accumulating vs. fail-fast validation.
- [ ] **Smart constructors** — hide the raw constructor; expose a validating builder that
      returns `Maybe`/`Either`.
- [ ] **Reader / Writer / State** — thread configuration, logs, and state explicitly
      instead of via globals or mutation.
- [ ] **Traversable / `traverse` / `sequence`** — flip `f (g a)` to `g (f a)`; run an
      effect across a structure.
- [ ] **Typeclass / interface-driven polymorphism** — program to laws (`Semigroup`,
      `Monoid`, `Functor`, `Monad`) rather than concrete types.
- [ ] **Pipelines & composition** — build behaviour by composing small total functions.

## Must Learn — Functional DDD

- [ ] **Parse, don't validate** — turn unstructured input into a precise type once, at the
      boundary, and carry the *parsed* type onward (no re-checking downstream).
- [ ] **Make illegal states unrepresentable** — choose types so invalid combinations
      simply cannot be constructed; prove it with a non-compiling `@ts-expect-error` case.
- [ ] **Value objects** — small immutable types with built-in invariants
      (e.g. `EmailAddress`, `Quantity`, `NonEmptyString`) via smart constructors / brands.
- [ ] **Workflows as functions** — a use case is `Input -> Result<Event[], Error>`; the
      type signature *is* the spec.
- [ ] **Domain events** — model outcomes as immutable event values that downstream steps
      react to.
- [ ] **Bounded contexts & the domain model** — keep the model expressed in domain terms,
      isolated from transport/persistence concerns.

## Must Learn — Functional core & imperative shell

- [ ] **Pure decision core** — all business logic as pure, total functions over plain
      data; no I/O inside.
- [ ] **Thin imperative shell** — I/O, time, randomness, persistence, and network live only
      at the edges; the shell gathers inputs, calls the core, and performs effects.
- [ ] **Boundaries** — pass data *in* and return decisions/events *out*; the core never
      reaches outward.
- [ ] **Testability** — exercise the core with fast, deterministic, example-based tests;
      keep the (few) integration tests at the shell.
- [ ] **Dependency inversion via values/functions** — inject effects as parameters
      (functions/handlers), not ambient singletons.

## Definition of Done

A topic is **done** when:

- [ ] Every Haskell example **type-checks and runs** under `mise exec -- runghc <file>.hs`
      (GHC 8.10.7, `base` only, offline).
- [ ] Every TypeScript example **type-checks** under the documented offline `tsc`
      command (`--noEmit --strict --target es2022 --module nodenext --moduleResolution
      nodenext --allowImportingTsExtensions --skipLibCheck`).
- [ ] Every TypeScript runtime example **runs green** under `mise exec -- node <file>.ts`
      using `node:assert/strict`, exiting non-zero on failure.
- [ ] At least one **negative** type-level case per type-level/DDD topic is pinned with
      `// @ts-expect-error` (TS) or shown as a rejected program (Haskell), proving the
      compiler rejects illegal states.
- [ ] Each example is **self-contained** and uses no networked dependencies.
- [ ] The topic folder has a short `README` linking back to the relevant
      [`learning-resources.md`](./learning-resources.md) entries.
- [ ] All commands in this repo run **offline** and nothing is committed without an
      explicit request.
