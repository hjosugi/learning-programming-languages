;;;; test/test.lisp --- The plain-SBCL test runner. Run with:
;;;;     sbcl --script test/test.lisp
;;;;
;;;; Loads the SHAPES library (offline, no ASDF/Quicklisp), loads the shared
;;;; test definitions in test/suite.lisp, runs them, and translates the failure
;;;; count into a process exit code.
;;;;
;;;; Exit contract (required by the verifier):
;;;;   * exit code 0 if EVERY assertion passes,
;;;;   * exit code 1 if ANY assertion fails.

(let ((here (or *load-pathname* *compile-file-pathname*)))
  ;; 1. Load the library, relative to this file (works from any directory).
  (load (merge-pathnames "../src/load.lisp" here))
  ;; 2. Load the test definitions.
  (load (merge-pathnames "suite.lisp" here)))

(in-package :shapes)

(let ((failures (run-tests)))
  (sb-ext:exit :code (if (zerop failures) 0 1)))
