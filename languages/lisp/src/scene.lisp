;;;; scene.lisp --- Higher-order functions, closures, and scene analytics.
;;;;
;;;; A SCENE is just a collection of shapes.  This file is the functional-
;;;; programming showcase: we lean on MAPCAR, REDUCE, REMOVE-IF, SORT, and
;;;; lexical CLOSURES, and we hand functions around as ordinary values.
;;;;
;;;; Closures matter in Lisp: a lambda captures its enclosing lexical
;;;; environment, which is how MEMOIZE below can keep a private hash table
;;;; alive across calls without any global state.

(in-package :shapes)

;;; ---------------------------------------------------------------------------
;;; The SCENE container (a small struct -- structs are the lightweight option
;;; when you don't need CLOS dispatch).
;;; ---------------------------------------------------------------------------

(defstruct (scene (:constructor %make-scene))
  (shapes '() :type list))

(defun make-scene (&rest shapes)
  "Build a scene from any number of shape objects."
  (%make-scene :shapes (copy-list shapes)))

(defun add-shape (scene shape)
  "Push SHAPE onto SCENE (returns the scene for chaining)."
  (push shape (scene-shapes scene))
  scene)

;;; ---------------------------------------------------------------------------
;;; Higher-order analytics
;;; ---------------------------------------------------------------------------

(defun areas (scene)
  "Map AREA over every shape -> list of areas. (Generic function as a value.)"
  ;; #'area passes the AREA generic function itself to MAPCAR.
  (mapcar #'area (scene-shapes scene)))

(defun total-area (scene)
  "REDUCE the per-shape areas into a single sum.
Signals EMPTY-SCENE-ERROR when there is nothing to total."
  (when (null (scene-shapes scene))
    (error 'empty-scene-error))
  (reduce #'+ (areas scene)))

(defun largest-shape (scene)
  "Return the shape with the greatest area using REDUCE with a closure."
  (when (null (scene-shapes scene))
    (error 'empty-scene-error))
  (reduce (lambda (a b) (if (>= (area a) (area b)) a b))
          (scene-shapes scene)))

(defun scaled-areas (scene factor)
  "Demonstrate a CLOSURE: build a one-arg scaler that captures FACTOR,
then MAPCAR it over the areas."
  (let ((scale (lambda (x) (* factor x))))   ; closes over FACTOR
    (mapcar scale (areas scene))))

(defun shapes-larger-than (scene threshold)
  "REMOVE-IF with a predicate closure that captures THRESHOLD."
  (remove-if (lambda (s) (<= (area s) threshold))
             (scene-shapes scene)))

(defun summarize-scene (scene)
  "Return a multi-line report string built with MAPCAR + FORMAT.
Pure: it does not print; the caller decides where the text goes."
  (if (null (scene-shapes scene))
      "<empty scene>"
      (let* ((lines (mapcar #'describe-shape (scene-shapes scene)))
             (count (length lines)))
        (format nil "~{  - ~A~%~}  total area: ~,3F across ~D shape~:P"
                lines (total-area scene) count))))

;;; ---------------------------------------------------------------------------
;;; MEMOIZE: a closure-returning higher-order function
;;; ---------------------------------------------------------------------------

(defun memoize (fn)
  "Return a memoized version of the single-argument function FN.

The returned closure owns a private hash table (captured lexically), so the
cache is invisible to everyone else and survives between calls.  This is the
canonical demonstration of closures-as-objects in Lisp."
  (let ((cache (make-hash-table :test #'equal)))
    (lambda (arg)
      (multiple-value-bind (value present-p) (gethash arg cache)
        (if present-p
            value
            (setf (gethash arg cache) (funcall fn arg)))))))
