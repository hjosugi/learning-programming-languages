;;;; macros.lisp --- The macro showcase: a resource macro + a tiny test DSL.
;;;;
;;;; Macros are Lisp's signature feature: they are functions that run at
;;;; COMPILE time, take *unevaluated code* (lists/symbols) as input, and return
;;;; new code to be compiled in place.  Because Lisp source IS Lisp data
;;;; (homoiconicity), we manipulate programs with the same tools we use for
;;;; lists.
;;;;
;;;; This file builds two non-trivial macros:
;;;;
;;;;   1. WITH-SCENE -- a `with-' style resource macro.  It binds a fresh
;;;;      scene, runs the body with shapes added, and on the way out prints a
;;;;      summary EVEN IF the body unwinds via a non-local exit (UNWIND-PROTECT).
;;;;      It uses quasiquote (`), unquote (,), splice (,@), and GENSYM for
;;;;      hygiene.
;;;;
;;;;   2. DEFTEST / RUN-TESTS -- a miniature testing DSL.  DEFTEST registers a
;;;;      named test; the IS clause is itself a macro that captures the source
;;;;      expression so failures can report what was actually evaluated.

(in-package :shapes)

;;; ===========================================================================
;;; 1. WITH-SCENE : a resource macro
;;; ===========================================================================

(defmacro with-scene ((scene-var &rest initial-shapes) &body body)
  "Bind SCENE-VAR to a fresh scene pre-populated with INITIAL-SHAPES, run BODY,
and guarantee a summary line is printed on exit (normal or non-local).

Usage:
  (with-scene (s (make-circle 2) (make-square 3))
    (add-shape s (make-rectangle 2 5))
    (total-area s))

Expansion sketch:
  (let ((s (make-scene <circle> <square>)))
    (unwind-protect
         (progn <body>)
      (format t \"~&; scene summary:~%~A~%\" (summarize-scene s))))"
  ;; GENSYM avoids capturing a user variable named, say, RESULT.
  (let ((result (gensym "RESULT")))
    `(let ((,scene-var (make-scene ,@initial-shapes)))   ; ,@ splices the list
       (unwind-protect
            (let ((,result (progn ,@body)))              ; ,@body splices forms
              ,result)
         ;; Cleanup always runs -- this is the "resource release" half.
         (format t "~&; scene summary:~%~A~%" (summarize-scene ,scene-var))))))

;;; ===========================================================================
;;; 2. A tiny test DSL : DEFTEST / IS / RUN-TESTS
;;; ===========================================================================

(defvar *tests* '()
  "Registry of (name . thunk) pairs, newest first. Each thunk returns
(values passed-count failed-count failure-messages).")

(defvar *recorder* nil
  "Dynamically bound by DEFTEST's thunk to a function (status &optional msg).
IS calls it.  Using a dynamic variable instead of returning closures means an
IS clause works no matter how deeply it is nested inside LET/DOLIST/WHEN/etc.")

(defun reset-tests ()
  "Clear the test registry (handy when re-loading a file in the REPL)."
  (setf *tests* '()))

(defun record-result (status &optional message)
  "Forward an assertion result to the test currently running.
Errors loudly if called outside a DEFTEST body."
  (if *recorder*
      (funcall *recorder* status message)
      (error "IS used outside of a DEFTEST body.")))

(defmacro is (form &optional description)
  "Assertion clause for DEFTEST.

Captures FORM *as source* (via ',form) so a failure can show the expression
text, not just NIL.  Evaluating an IS form records exactly one pass/fail into
the enclosing test via the dynamic *RECORDER*, so IS may appear anywhere inside
the test body -- top level, inside a LET, a DOLIST, a WHEN, and so on."
  (let ((value (gensym "VALUE")))
    `(let ((,value (ignore-errors ,form)))
       (if ,value
           (record-result :pass)
           (record-result :fail
                          (format nil "~A: ~S returned NIL"
                                  (or ,description "assertion")
                                  ',form)))
       ,value)))

(defmacro deftest (name &body body)
  "Define and register a test named NAME. BODY is ordinary Lisp code that may
contain any number of IS assertions anywhere within it.

DEFTEST stores a thunk in *TESTS*; running the thunk binds *RECORDER* to a
local tally function and evaluates BODY, so every IS reached at runtime is
counted.  Re-defining a test with the same NAME replaces the old one."
  (let ((passed  (gensym "PASSED"))
        (failed  (gensym "FAILED"))
        (msgs    (gensym "MSGS"))
        (status  (gensym "STATUS"))
        (message (gensym "MESSAGE")))
    `(progn
       ;; Drop any prior test of the same name, then register the new thunk.
       (setf *tests* (remove ',name *tests* :key #'car))
       (push
        (cons ',name
              (lambda ()
                (let ((,passed 0) (,failed 0) (,msgs '()))
                  (flet ((tally (,status &optional ,message)
                           (ecase ,status
                             (:pass (incf ,passed))
                             (:fail (incf ,failed)
                                    (push ,message ,msgs)))))
                    (let ((*recorder* #'tally))
                      ,@body)
                    (values ,passed ,failed (nreverse ,msgs))))))
        *tests*)
       ',name)))

(defun run-tests (&key (stream *standard-output*))
  "Run every registered test (in definition order) and print a summary.

Returns the total number of FAILED assertions, so a caller can translate that
into a process exit code.  This is what test/test.lisp does."
  (let ((total-pass 0)
        (total-fail 0))
    ;; *TESTS* is newest-first; reverse so output matches definition order.
    (dolist (entry (reverse *tests*))
      (destructuring-bind (name . thunk) entry
        (multiple-value-bind (pass fail messages) (funcall thunk)
          (incf total-pass pass)
          (incf total-fail fail)
          (format stream "~&~:[FAIL~;ok  ~] ~A  (~D passed, ~D failed)~%"
                  (zerop fail) name pass fail)
          (dolist (m messages)
            (format stream "        - ~A~%" m)))))
    (format stream "~&----------------------------------------~%")
    (format stream "~:[SOME TESTS FAILED~;ALL TESTS PASSED~]: ~D passed, ~D failed.~%"
            (zerop total-fail) total-pass total-fail)
    total-fail))
