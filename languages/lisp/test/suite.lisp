;;;; test/suite.lisp --- Test definitions (shared by the script and ASDF).
;;;;
;;;; This file only DEFINES tests via the project's DEFTEST/IS DSL; it does not
;;;; run them or exit.  Two entry points reuse it:
;;;;   * test/test.lisp     -- plain `sbcl --script` runner (exits 0/1).
;;;;   * test/asdf-tests.lisp -- the ASDF test-op component.
;;;;
;;;; It assumes the SHAPES system is already loaded.

(in-package :shapes)

(reset-tests)

(defun close-to (a b &optional (eps 1d-9))
  (< (abs (- a b)) eps))

;;; --- CLOS: areas, perimeters, polymorphism --------------------------------

(deftest circle-geometry
  (is (close-to (area (make-circle 2)) (* pi 4)) "circle area = pi r^2")
  (is (close-to (perimeter (make-circle 2)) (* 2 pi 2)) "circle perimeter = 2 pi r"))

(deftest rectangle-geometry
  (is (= (area (make-rectangle 3 4)) 12) "rectangle area = w*h")
  (is (= (perimeter (make-rectangle 3 4)) 14) "rectangle perimeter = 2(w+h)"))

(deftest triangle-geometry
  (is (= (area (make-triangle 6 4)) 12) "triangle area = base*height/2")
  (is (= (perimeter (make-triangle 6 4 '(3 4 5))) 12) "triangle perimeter = sum of sides"))

;;; --- CLOS: inheritance / polymorphism -------------------------------------

(deftest square-inherits-rectangle
  ;; SQUARE has NO area method of its own; it must inherit RECTANGLE's.
  (is (= (area (make-square 5)) 25) "square reuses rectangle AREA via inheritance")
  (is (typep (make-square 5) 'rectangle) "square IS-A rectangle")
  (is (= (rectangle-width (make-square 7)) (rectangle-height (make-square 7)))
      "square forces width = height at init"))

(deftest describe-shape-around-method
  ;; The :around method prepends [CLASSNAME]; check it actually fires.
  (is (search "[CIRCLE]" (describe-shape (make-circle 1)))
      ":around method tags the class name")
  (is (search "[SQUARE]" (describe-shape (make-square 2)))
      ":around method works through inheritance"))

;;; --- Higher-order functions: mapcar / reduce / closures -------------------

(deftest scene-totals
  (let ((scene (make-scene (make-rectangle 2 3) (make-square 4) (make-triangle 4 5))))
    (is (= (length (areas scene)) 3) "AREAS maps over every shape")
    (is (= (total-area scene) (+ 6 16 10)) "TOTAL-AREA reduces with +")
    (is (= (area (largest-shape scene)) 16) "LARGEST-SHAPE picks max by area")))

(deftest scaled-areas-closure
  (let ((scene (make-scene (make-rectangle 2 3) (make-square 4))))
    (is (equal (scaled-areas scene 10) '(60 160))
        "SCALED-AREAS closes over the scale factor")))

(deftest memoize-caches
  (let* ((calls 0)
         (fast (memoize (lambda (s) (incf calls) (area s))))
         (sq (make-square 3)))
    (funcall fast sq) (funcall fast sq) (funcall fast sq)
    (is (= calls 1) "memoized closure computes once for repeated args")
    (is (= (funcall fast sq) 9) "memoized closure returns the right value")))

;;; --- Macro: WITH-SCENE resource macro -------------------------------------

(deftest with-scene-macro
  ;; Capture the auto-printed summary so it doesn't pollute test output, and
  ;; confirm the macro both runs the body and releases (prints) on exit.
  (let* ((summary
           (with-output-to-string (*standard-output*)
             (let ((total (with-scene (s (make-circle 1) (make-square 2))
                            (add-shape s (make-triangle 3 4 '(3 4 5)))
                            (total-area s))))
               (declare (ignore total)))))
         (body-result
           (let ((*standard-output* (make-string-output-stream)))
             (with-scene (s (make-square 2))   ; area 4
               (+ (total-area s) 100)))))      ; body value flows out
    (is (search "scene summary" summary) "WITH-SCENE prints a summary on exit")
    (is (= body-result 104) "WITH-SCENE returns the body's value")))

(deftest with-scene-cleanup-on-unwind
  ;; The summary must print even when the body does a non-local exit.
  (let ((summary
          (with-output-to-string (*standard-output*)
            (ignore-errors
             (with-scene (s (make-square 3))
               (error "boom"))))))         ; abort the body
    (is (search "scene summary" summary)
        "WITH-SCENE cleanup runs through UNWIND-PROTECT even on error")))

;;; --- Condition system: errors + restarts ----------------------------------

(deftest invalid-dimension-signalled
  (is (typep (nth-value 1 (ignore-errors (make-circle -1))) 'invalid-dimension)
      "negative radius signals INVALID-DIMENSION")
  (is (typep (nth-value 1 (ignore-errors (make-circle 0))) 'invalid-dimension)
      "zero radius signals INVALID-DIMENSION")
  (is (typep (nth-value 1 (ignore-errors (make-rectangle 2 -3))) 'geometry-error)
      "INVALID-DIMENSION is a subtype of GEOMETRY-ERROR"))

(deftest empty-scene-signalled
  (is (typep (nth-value 1 (ignore-errors (total-area (make-scene)))) 'empty-scene-error)
      "TOTAL-AREA on empty scene signals EMPTY-SCENE-ERROR"))

(deftest restart-recovers
  ;; HANDLER-BIND + INVOKE-RESTART repairs a bad dimension instead of unwinding.
  (let ((fixed
          (handler-bind
              ((invalid-dimension
                 (lambda (e)
                   (declare (ignore e))
                   (invoke-restart (find-restart 'use-value) 8))))
            (make-square -4))))   ; width -4 -> corrected to 8 -> square 8x8
    (is (= (area fixed) 64) "USE-VALUE restart substitutes a corrected dimension")))

(deftest handler-case-traps
  (is (eq :caught
          (handler-case (perimeter (make-triangle 3 4))   ; no sides -> error
            (geometry-error () :caught)))
      "HANDLER-CASE traps the missing-sides geometry error"))
