# Learning Lisp

A thorough, idiomatic hands-on for **Common Lisp (SBCL)**: the REPL workflow,
functions & recursion, higher-order functions, **macros**, **CLOS**
(classes / generic functions / methods / inheritance), and **condition
handling** (`define-condition` / `handler-case` / restarts).

The hands-on is a small but real **shapes library**: a CLOS class hierarchy
whose `area`/`perimeter` are generic functions, a functional analytics layer
over a "scene" of shapes, a non-trivial `with-scene` resource macro, a tiny
`deftest`/`is` testing DSL built entirely out of macros, and a geometry
condition hierarchy with a recovery restart.

Last verified: 2026-06-21

## How this repo is organized

```
learning-lisp/
├── README.md                      <- you are here (Run / Test / Walkthrough / Exercises)
├── shapes.asd                     <- ASDF system (the upgrade path; optional)
├── src/
│   ├── load.lisp                  <- offline loader used by `sbcl --script`
│   ├── packages.lisp              <- package + exports (the public API)
│   ├── conditions.lisp            <- define-condition hierarchy + a restart
│   ├── shapes.lisp                <- CLOS: defclass / defgeneric / defmethod
│   ├── scene.lisp                 <- higher-order fns: mapcar / reduce / closures
│   ├── macros.lisp                <- WITH-SCENE resource macro + DEFTEST DSL
│   └── main.lisp                  <- runnable demo (entry point)
├── test/
│   ├── suite.lisp                 <- the 14 tests (26 assertions), shared
│   └── test.lisp                  <- `sbcl --script` runner (exit 0/1)
└── docs/
    ├── 2026-learning-items.md     <- named learning targets + Definition of Done
    └── learning-resources.md      <- canonical primary sources
```

The demo (`src/main.lisp`) is the guided tour; the test suite
(`test/suite.lisp`) is the rigorous proof that every feature behaves.

## Toolchain

SBCL (Steel Bank Common Lisp) 2.6.5 is installed here **via mise** and is *not*
on the bare `PATH`, so every command is prefixed with `mise exec --`.

Install on another machine:

```bash
mise use -g sbcl@latest      # via mise (what this repo uses)
# or, on Arch Linux:
sudo pacman -S sbcl
# or, on Debian/Ubuntu:  sudo apt install sbcl
# or, on macOS:          brew install sbcl
```

No Quicklisp, no internet, no external libraries are needed for the primary
commands below — only standard Common Lisp plus SBCL's `sb-ext`.

## Run

Runs the demo (CLOS dispatch, higher-order functions, the macro, conditions,
restarts, and the inline test DSL) and prints to stdout:

```bash
mise exec -- sbcl --script languages/lisp/src/main.lisp
```

## Test

Non-interactive. Exits **0** when all assertions pass, **1** on any failure:

```bash
mise exec -- sbcl --script languages/lisp/test/test.lisp
```

Expected tail:

```
----------------------------------------
ALL TESTS PASSED: 26 passed, 0 failed.
```

## The REPL workflow (recommended way to learn)

`--script` is for batch runs; the *real* Lisp experience is the interactive
REPL, where you redefine functions, classes, and methods in a running image:

```bash
mise exec -- sbcl
```

```lisp
;; In the REPL:
(load "languages/lisp/src/load.lisp")  ; load the library
(in-package :shapes)
(area (make-circle 2))                 ; => 12.566...
(describe-shape (make-square 4))       ; => "[SQUARE] square with area 16.000"
(defmethod area ((c circle)) 42)       ; redefine a method live...
(area (make-circle 2))                 ; => 42  (no restart needed!)
,quit                                  ; or (sb-ext:exit)
```

This redefine-in-place loop (ideally driven from SLIME or Sly in your editor)
is the heart of Lisp development.

## Upgrade path

This repo runs offline with plain SBCL on purpose. When you want the real,
heavier tooling:

- **ASDF** (already wired): `shapes.asd` defines `:shapes` and `:shapes/test`.
  ```lisp
  (require :asdf)
  (push #p"languages/lisp/" asdf:*central-registry*)
  (asdf:load-system :shapes)     ; compile + load the library
  (asdf:test-system :shapes)     ; load + run the suite (errors on failure)
  ```
- **Quicklisp** — the de-facto package manager. After installing it, symlink
  this directory into `~/quicklisp/local-projects/` and use
  `(ql:quickload :shapes)`. Then you can pull real libraries (e.g. `alexandria`).
- **FiveAM / Rove** — replace the hand-rolled `deftest`/`is` DSL with a
  production test framework. The DSL here is intentionally tiny so you can see
  how `def-suite`/`test`/`is` are *built*; FiveAM gives fixtures, random
  testing, and richer reporting.
- **SLIME / Sly** — editor-integrated REPLs (Emacs). Interactive macroexpansion
  (`C-c C-m`), jump-to-definition, inline evaluation, and a graphical debugger
  with clickable restarts — the natural next step after the bare REPL above.
- **Delivery** — `sb-ext:save-lisp-and-die` to ship a standalone executable.

## Walkthrough

The four signature Common Lisp features this code demonstrates:

### 1. CLOS — classes, generic functions, methods, inheritance (`src/shapes.lisp`)

- `defclass` defines `shape` and the subclasses `circle`, `rectangle`,
  `square` (a subclass of `rectangle`), and `triangle`. Slots use `:initarg`,
  `:accessor`, `:initform`, and `:default-initargs`.
- `defgeneric` declares the `area`/`perimeter`/`describe-shape` **protocols**;
  `defmethod` supplies implementations selected by the *type of the argument*
  (single dispatch = polymorphism). Methods are not "inside" classes — they
  belong to the generic function.
- **Inheritance/polymorphism in action:** `square` deliberately defines *no*
  `area` method. `(area (make-square 4))` works because it inherits
  `rectangle`'s method. `square` only specializes `initialize-instance :after`
  to force width = height.
- **Method combination:** `describe-shape` has an `:around` method that wraps
  every primary method (it prepends `[CLASSNAME]` and calls `call-next-method`).
- **Validation through CLOS:** `initialize-instance :after` methods run after
  slots are filled and route every dimension through the condition system, so
  you cannot construct a degenerate shape.

### 2. Higher-order functions & closures (`src/scene.lisp`)

- `areas` does `(mapcar #'area shapes)` — passing the *generic function itself*
  as a value.
- `total-area` / `largest-shape` use `reduce` (with `#'+` and with a `lambda`
  comparator).
- `scaled-areas` and `shapes-larger-than` build **closures** that capture a
  factor / threshold lexically.
- `memoize` is the canonical closure-as-object: it returns a `lambda` that owns
  a private hash table, invisible to callers and persistent across calls.

### 3. Macros (`src/macros.lisp`)

- `with-scene` is a `with-`style **resource macro**. It binds a fresh scene,
  splices the body in (`,@body`), and uses `unwind-protect` so a summary always
  prints on exit — even if the body throws. It uses quasiquote/unquote/splice
  and `gensym` for hygiene.
- `deftest` / `is` is a **mini testing DSL**. `is` captures its expression *as
  source* (`',form`) so a failure can report the exact code that returned NIL,
  and records the result through a dynamically-bound recorder so an `is` works
  anywhere — even nested inside a `let`, `dolist`, or `when`. `deftest`
  registers a thunk in `*tests*`; `run-tests` runs them all and returns the
  failure count. The whole project's test suite is built on this DSL.

### 4. Condition handling (`src/conditions.lisp`)

- `define-condition` builds an error hierarchy:
  `error → geometry-error → {invalid-dimension, empty-scene-error}`.
- Conditions are CLOS objects with slots (`:name`, `:value`) and a `:report`
  function controlling how they print.
- `check-positive` signals `invalid-dimension` inside a `restart-case` that
  offers a `use-value` **restart** — so a handler can *repair* a bad dimension
  and continue instead of unwinding. `src/main.lisp` and the `restart-recovers`
  test both exercise `handler-bind` + `invoke-restart` to recover live.
- `handler-case` is used for the simpler "trap and translate" pattern.

## Exercises

Progressive next steps — each builds on the last:

1. **New shape (easy).** Add an `ellipse` class with `semi-major`/`semi-minor`
   slots and `area`/`perimeter` methods (use Ramanujan's perimeter
   approximation). Add tests to `test/suite.lisp` and watch the count rise.

2. **New generic (easy/medium).** Define a `scale` generic function that
   returns a *new* shape enlarged by a factor (e.g. `(scale circle 2)` doubles
   the radius). Add a `square` method that delegates to `rectangle` via
   `call-next-method`, then prove `(area (scale sq 3))` is 9× the original.

3. **Multiple dispatch (medium).** Add `(defgeneric same-area-p (a b))` with
   methods specialized on *both* arguments — the feature that truly separates
   CLOS from single-dispatch OO. Add a method that short-circuits when the two
   shapes are the same class.

4. **Grow the macro (medium).** Extend `with-scene` to accept options, e.g.
   `(with-scene (s :silent t) ...)` to suppress the summary, or
   `(with-scene (s :on-exit #'my-fn) ...)` to run a custom cleanup. Keep it
   hygienic with `gensym`.

5. **Grow the DSL (medium/hard).** Add `is-error` to the test DSL: an assertion
   that passes only if its body signals a given condition type
   (`(is-error invalid-dimension (make-circle -1))`). Then add `signals` and a
   `is=` that prints the expected vs. actual values on failure.

6. **Port to FiveAM (hard).** Install Quicklisp, `(ql:quickload :fiveam)`, and
   rewrite `test/suite.lisp` using `def-suite` / `test` / `is`. Compare the
   ergonomics with the hand-rolled DSL and note what the framework gives you
   (fixtures, `is-true`/`signals`, random testing, reporting).
