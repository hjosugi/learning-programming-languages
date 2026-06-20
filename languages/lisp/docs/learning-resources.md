# Further learning resources

Last verified: 2026-06-21

Curated, canonical primary sources for this repo's named learning technology:
**Common Lisp** (the language + standard) and **SBCL** (the implementation),
covering the REPL workflow, macros, CLOS, and the condition system. Prefer
these over blog posts; they are the reference line this repo follows.

## The language and standard

- **Common Lisp HyperSpec (CLHS)** — http://www.lispworks.com/documentation/HyperSpec/Front/
  The hyperlinked ANSI Common Lisp standard. The authoritative reference for
  every symbol used in this repo (`defclass`, `defgeneric`, `defmethod`,
  `define-condition`, `restart-case`, `mapcar`, `reduce`, `unwind-protect`, …).

- **lisp-lang.org** — https://lisp-lang.org
  The community front door: "why Lisp", a learning path, and pointers to the
  ecosystem. A good orientation before diving into the spec.

## The implementation (what this repo runs on)

- **SBCL home / manual** — http://www.sbcl.org and http://www.sbcl.org/manual/
  Steel Bank Common Lisp: download, the `--script` flag, `sb-ext` extensions
  (e.g. `sb-ext:exit`, `save-lisp-and-die`), and implementation notes. This is
  the compiler the repo's primary commands invoke.

## Books (canonical, free online)

- **Practical Common Lisp — Peter Seibel** — https://gigamonkeys.com/book/
  The standard modern introduction. Read the chapters on macros, CLOS
  (objects/generic functions), and conditions/restarts — they map directly onto
  `src/macros.lisp`, `src/shapes.lisp`, and `src/conditions.lisp`.

- **Common Lisp the Language, 2nd ed. (CLtL2) — Guy L. Steele** —
  https://www.cs.cmu.edu/Groups/AI/html/cltl/cltl2.html
  The pre-ANSI reference; still excellent prose on CLOS and the condition
  system, including the rationale the HyperSpec omits.

- **On Lisp — Paul Graham** — https://www.paulgraham.com/onlisp.html
  The deep dive on macros and bottom-up programming. The reference for building
  DSLs like this repo's `deftest`/`is`, plus hygiene and macro pitfalls.

- **Gentle Introduction to Symbolic Computation — David S. Touretzky** —
  https://www.cs.cmu.edu/~dst/LispBook/
  A gentle on-ramp to functions, recursion, and list processing if Practical
  Common Lisp moves too fast.

## Ecosystem / upgrade path

- **ASDF manual** — https://asdf.common-lisp.dev/asdf.html
  The build/system-definition tool. Reference for `defsystem`, components,
  `:serial`, and `test-op` — the basis of this repo's `shapes.asd`.

- **Quicklisp** — https://www.quicklisp.org/beta/
  The de-facto library manager. How to install it and `ql:quickload` systems;
  the gateway to FiveAM, Rove, Alexandria, and the wider library ecosystem.

- **FiveAM** — https://fiveam.common-lisp.dev/
  A widely used regression test framework — the production replacement for this
  repo's hand-rolled test DSL (`def-suite`, `test`, `is`, `signals`).

- **The SLIME manual** — https://slime.common-lisp.dev/doc/html/
  Emacs's Superior Lisp Interaction Mode: editor-integrated REPL, inline
  evaluation, macroexpansion, and the interactive debugger — the natural next
  step after the bare `sbcl` REPL.
