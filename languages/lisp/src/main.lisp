;;;; main.lisp --- Demo entry point. Run with:  sbcl --script src/main.lisp
;;;;
;;;; This driver loads the SHAPES system and exercises every showcased feature
;;;; so you can SEE the behaviour, not just read about it:
;;;;   * CLOS generic-function dispatch + inheritance (square uses rectangle).
;;;;   * Higher-order functions (mapcar / reduce / closures / memoize).
;;;;   * The WITH-SCENE resource macro (note the guaranteed summary line).
;;;;   * Condition handling (handler-case) and a RESTART (use-value).
;;;;
;;;; It prints to stdout and exits 0.  The actual assertions live in
;;;; test/test.lisp.

;; Load the library relative to this file so it works from any directory.
(load (merge-pathnames "load.lisp" (or *load-pathname* *compile-file-pathname*)))

(in-package :shapes)

(defun banner (text)
  (format t "~&~%==== ~A ====~%" text))

(defun run-demo ()
  (banner "CLOS: generic functions, dispatch, and inheritance")
  (let ((c (make-circle 2))
        (r (make-rectangle 3 4))
        (sq (make-square 5))                 ; square inherits rectangle's AREA
        (tri (make-triangle 6 4 '(3 4 5))))
    (dolist (s (list c r sq tri))
      ;; DESCRIBE-SHAPE uses an :around method to prepend the class name.
      (format t "~A~%" (describe-shape s)))
    (format t "square area via INHERITED rectangle method = ~A~%" (area sq))
    (format t "circle perimeter = ~,4F~%" (perimeter c)))

  (banner "Higher-order functions: mapcar / reduce / closures")
  (let ((scene (make-scene (make-circle 1) (make-rectangle 2 3) (make-square 4))))
    (format t "areas        = ~{~,3F ~}~%" (areas scene))
    (format t "total-area   = ~,3F~%" (total-area scene))
    (format t "scaled x10   = ~{~,3F ~}~%" (scaled-areas scene 10))
    (format t "largest      = ~A~%" (describe-shape (largest-shape scene))))

  (banner "Closures: a memoized, instrumented area function")
  (let* ((calls 0)
         (slow-area (lambda (s) (incf calls) (area s)))
         (fast (memoize slow-area))
         (sq (make-square 3)))
    (funcall fast sq) (funcall fast sq) (funcall fast sq)
    (format t "memoized: computed ~D time(s) for 3 calls (expected 1)~%" calls))

  (banner "Macro: WITH-SCENE resource macro (auto-prints a summary on exit)")
  (let ((sum (with-scene (s (make-circle 1) (make-square 2))
               (add-shape s (make-triangle 3 4 '(3 4 5)))
               (total-area s))))
    (format t "body returned total-area = ~,3F~%" sum))

  (banner "Conditions: handler-case traps a domain error")
  (handler-case
      (make-circle -5)                       ; signals INVALID-DIMENSION
    (invalid-dimension (e)
      (format t "caught: ~A~%" e)))

  (banner "Restarts: recover from a bad dimension with USE-VALUE")
  (handler-bind
      ((invalid-dimension
         (lambda (e)
           (declare (ignore e))
           ;; Instead of unwinding, substitute a sane value and continue.
           (let ((restart (find-restart 'use-value)))
             (when restart (invoke-restart restart 10))))))
    (let ((fixed (make-rectangle -2 5)))     ; width -2 gets corrected to 10
      (format t "rectangle recovered to area = ~,3F~%" (area fixed))))

  (banner "DSL macro: define + run a couple of inline tests")
  (reset-tests)
  (deftest demo-circle-area
    (is (< (abs (- (area (make-circle 1)) pi)) 1d-9) "unit circle area ~= pi"))
  (deftest demo-square-inherits
    (is (= (area (make-square 4)) 16) "4x4 square area = 16"))
  (let ((failures (run-tests)))
    (format t "~&(demo DSL reported ~D failure(s))~%" failures))

  (banner "Done")
  (values))

(run-demo)
(sb-ext:exit :code 0)
