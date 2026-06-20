;;;; shapes.asd --- ASDF system definition (the "upgrade path").
;;;;
;;;; ASDF (Another System Definition Facility) is Common Lisp's de-facto build
;;;; system: it knows how to compile and load a set of files in dependency
;;;; order.  The PRIMARY workflow in this repo does NOT need ASDF -- plain
;;;; `sbcl --script src/main.lisp` works offline via src/load.lisp.  This file
;;;; is here so you can grow toward the real tooling (Quicklisp, FiveAM/Rove,
;;;; SLIME) once you want it.
;;;;
;;;; Once this directory is on ASDF's search path you can do, from a REPL:
;;;;
;;;;   (require :asdf)
;;;;   (push #p"/mnt/data/workspace/learning-lisp/" asdf:*central-registry*)
;;;;   (asdf:load-system :shapes)        ; load the library
;;;;   (asdf:test-system :shapes)        ; load + run the test system
;;;;
;;;; or simply `(ql:quickload :shapes)` after installing Quicklisp.

(asdf:defsystem #:shapes
  :description "A tiny CLOS shapes library showcasing macros, generic
functions, higher-order functions, and the condition system."
  :author "learning-lisp"
  :license "MIT"
  :version "0.1.0"
  :serial t                       ; compile/load files in the listed order
  :components ((:module "src"
                :serial t
                :components ((:file "packages")
                             (:file "conditions")
                             (:file "shapes")
                             (:file "scene")
                             (:file "macros"))))
  :in-order-to ((asdf:test-op (asdf:test-op #:shapes/test))))

(asdf:defsystem #:shapes/test
  :description "Test system for SHAPES. Uses the project's own DEFTEST DSL."
  :depends-on (#:shapes)
  :serial t
  :components ((:module "test"
                :components ((:file "suite"))))
  :perform (asdf:test-op (op component)
             ;; Run the suite; signal an error (so test-system fails) on failure.
             (let ((failures (uiop:symbol-call :shapes '#:run-tests)))
               (unless (zerop failures)
                 (error "~D test assertion(s) failed." failures)))))
