;;;; conditions.lisp --- The geometry condition hierarchy.
;;;;
;;;; Common Lisp's condition system is far richer than exceptions in most
;;;; languages: conditions are CLOS objects, signalling does NOT unwind the
;;;; stack by itself, and handlers can choose RESTARTS to recover *without*
;;;; losing the computation.  Here we build a small hierarchy:
;;;;
;;;;     error  (standard)
;;;;       └── geometry-error            ; root of our domain errors
;;;;             ├── invalid-dimension   ; a negative/zero length etc.
;;;;             └── empty-scene-error   ; asked for a stat on no shapes
;;;;
;;;; `define-condition` is to conditions what `defclass` is to objects.

(in-package :shapes)

(define-condition geometry-error (error)
  ()
  (:documentation "Root of all errors raised by the shapes library.
Catch this with HANDLER-CASE to trap every domain-specific failure."))

(define-condition invalid-dimension (geometry-error)
  ;; Slots become readers; :initarg lets callers pass them at SIGNAL time.
  ((name  :initarg :name  :reader invalid-dimension-name
          :documentation "Which dimension was bad, e.g. :radius.")
   (value :initarg :value :reader invalid-dimension-value
          :documentation "The offending value the caller supplied."))
  (:report (lambda (condition stream)
             ;; :report controls how the condition prints to a stream,
             ;; e.g. when SBCL drops into the debugger.
             (format stream "Invalid dimension ~S = ~S (must be a positive real)."
                     (invalid-dimension-name condition)
                     (invalid-dimension-value condition))))
  (:documentation "Signalled when a shape is built with a non-positive size."))

(define-condition empty-scene-error (geometry-error)
  ()
  (:report "Operation requires at least one shape, but the scene is empty.")
  (:documentation "Signalled by statistics that are undefined on an empty scene."))

(defun check-positive (name value)
  "Validate that VALUE is a positive real, signalling INVALID-DIMENSION if not.

This demonstrates a RESTART: the handler may invoke USE-VALUE to substitute a
corrected dimension instead of unwinding the whole construction.  Returns the
accepted (possibly corrected) value."
  (loop
    (if (and (realp value) (plusp value))
        (return value)
        (restart-case
            (error 'invalid-dimension :name name :value value)
          (use-value (new-value)
            :report "Supply a replacement value for this dimension."
            :interactive (lambda ()
                           (format *query-io* "~&New value for ~S: " name)
                           (list (read *query-io*)))
            (setf value new-value))))))
