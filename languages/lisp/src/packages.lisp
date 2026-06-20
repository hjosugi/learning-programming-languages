;;;; packages.lisp --- Package definitions for the SHAPES learning system.
;;;;
;;;; A Common Lisp "package" is a namespace for symbols (it is NOT a module/
;;;; file system unit -- ASDF handles that).  We define one package that
;;;; exports the public API and `:use`s the standard CL package so we can
;;;; write `defun`, `mapcar`, etc. without a `cl:` prefix.
;;;;
;;;; Everything in this repo runs on plain SBCL with no external libraries,
;;;; so every symbol here comes either from the COMMON-LISP standard package
;;;; or is defined locally.

(defpackage :shapes
  (:use :common-lisp)
  ;; --- conditions (the geometry error protocol) ------------------------
  (:export #:geometry-error
           #:invalid-dimension
           #:invalid-dimension-name
           #:invalid-dimension-value
           #:empty-scene-error)
  ;; --- CLOS classes ----------------------------------------------------
  (:export #:shape
           #:circle
           #:rectangle
           #:square
           #:triangle
           #:make-circle
           #:make-rectangle
           #:make-square
           #:make-triangle)
  ;; --- generic functions / accessors -----------------------------------
  (:export #:area
           #:perimeter
           #:describe-shape
           #:shape-name)
  ;; --- scenes + higher-order analytics ---------------------------------
  (:export #:scene
           #:make-scene
           #:scene-shapes
           #:add-shape
           #:total-area
           #:largest-shape
           #:areas
           #:scaled-areas
           #:summarize-scene
           #:memoize)
  ;; --- the resource macro + the test DSL macro -------------------------
  (:export #:with-scene
           #:deftest
           #:run-tests
           #:*tests*
           #:reset-tests))
