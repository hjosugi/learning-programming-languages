# 2026 Learning Items: Common Lisp (SBCL)

Last verified: 2026-06-21

The named learning targets for this repo, with the hands-on project that
exercises each. The hands-on is a CLOS shapes library: see
[../README.md](../README.md) for Run/Test/Walkthrough.

## Must Learn

### The REPL workflow

- the read-eval-print loop as the primary dev surface
- loading files (`load`) vs scripting (`sbcl --script`)
- interactive redefinition (redefine a function/method/class in a live image)
- packages and `in-package`
- inspecting with `describe`, `inspect`, `documentation`
- exiting cleanly (`sb-ext:exit`, `(quit)`)
- (upgrade) SLIME / Sly for editor-driven evaluation and the graphical debugger

Outcome:

- Start SBCL, load `src/load.lisp`, call into `:shapes`, redefine a method and
  see the change without restarting.

### Functions & recursion

- `defun`, `lambda`, optional / `&rest` / keyword parameters
- multiple return values (`values`, `multiple-value-bind`, `nth-value`)
- `let` / `let*` / `flet` / `labels` (local + recursive bindings)
- recursion and the idea of tail position
- predicates and the truthiness of `nil`

Outcome:

- Read `scene.lisp` and explain each binding form and where multiple values
  are produced/consumed (e.g. `memoize`'s `gethash`).

### Higher-order functions

- functions as values (`#'name`, `function`)
- `mapcar`, `reduce`, `remove-if`, `sort`
- closures capturing the lexical environment
- returning functions (memoization)

Outcome:

- Explain how `memoize` keeps a private cache and why `scaled-areas` needs a
  closure.

### Macros

- code-as-data (homoiconicity); quote, quasiquote, unquote, splice
- `defmacro`, macroexpansion (`macroexpand-1`)
- hygiene with `gensym`
- `with-` resource macros and `unwind-protect`
- building a small DSL

Outcome:

- Macroexpand `with-scene` and `deftest`; explain every `,` `,@` and `gensym`.

### CLOS (classes / generic functions / methods)

- `defclass` with slots, `:initarg`, `:accessor`, `:initform`
- `defgeneric` / `defmethod` and single dispatch
- inheritance and method resolution
- `:before` / `:after` / `:around` method combination, `call-next-method`
- `initialize-instance :after`
- (stretch) multiple dispatch

Outcome:

- Explain why `(area (make-square 4))` works with no `square` method, and what
  the `:around` method on `describe-shape` adds.

### Condition handling

- `define-condition` and the condition class hierarchy
- `signal` / `error` / `:report`
- `handler-case` (trap + unwind) vs `handler-bind` (handle in place)
- restarts: `restart-case`, `find-restart`, `invoke-restart`, `use-value`
- why "signalling does not unwind" matters

Outcome:

- Trap an `invalid-dimension` with `handler-case`, then *recover* from it with
  `handler-bind` + the `use-value` restart, without rebuilding the shape.

## Definition of Done

- `mise exec -- sbcl --script src/main.lisp` runs the demo and exits 0.
- `mise exec -- sbcl --script test/test.lisp` runs the suite, prints a summary,
  exits 0 when all pass and 1 on any failure.
- The code shows all six targets above: REPL-loadable package, recursion/multiple
  values, higher-order functions + closures, a non-trivial macro **and** a DSL
  macro, a CLOS hierarchy with inheritance + `:around` combination, and a
  condition hierarchy with a working restart.
- `shapes.asd` loads via `asdf:load-system` and `asdf:test-system` (upgrade path).
- README documents Run, Test, the REPL workflow, the upgrade path, a Walkthrough,
  and 4–6 progressive Exercises.
