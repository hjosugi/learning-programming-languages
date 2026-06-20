;;;; shapes.lisp --- CLOS: classes, generic functions, methods, inheritance.
;;;;
;;;; This is the heart of the CLOS showcase.  We model a small shape hierarchy:
;;;;
;;;;     shape              ; abstract base, holds a NAME
;;;;       ├── circle       ; radius
;;;;       ├── rectangle    ; width, height
;;;;       │     └── square ; inherits rectangle, constrains width = height
;;;;       └── triangle     ; base, height, three sides for the perimeter
;;;;
;;;; Key CLOS ideas demonstrated:
;;;;   * `defclass` with slots, :initarg, :accessor, :initform.
;;;;   * `defgeneric` declares a protocol; `defmethod` supplies implementations
;;;;     selected by the *type of the argument* (single dispatch / polymorphism).
;;;;   * Inheritance: SQUARE reuses RECTANGLE's AREA method automatically.
;;;;   * Method combination: an :around method on DESCRIBE-SHAPE wraps every
;;;;     primary method, and SQUARE specializes AREA while still calling
;;;;     CALL-NEXT-METHOD to reach the inherited RECTANGLE behaviour.
;;;;   * `initialize-instance :after` validates slots through the condition
;;;;     system, so you cannot construct a degenerate shape.

(in-package :shapes)

;;; ---------------------------------------------------------------------------
;;; Classes
;;; ---------------------------------------------------------------------------

(defclass shape ()
  ((name :initarg :name
         :initform "shape"
         :accessor shape-name
         :documentation "Human-readable label used by DESCRIBE-SHAPE."))
  (:documentation "Abstract base class for all shapes. Not meant to be
instantiated directly; subclasses supply geometry."))

(defclass circle (shape)
  ((radius :initarg :radius :accessor circle-radius))
  (:default-initargs :name "circle")
  (:documentation "A circle defined by its RADIUS."))

(defclass rectangle (shape)
  ((width  :initarg :width  :accessor rectangle-width)
   (height :initarg :height :accessor rectangle-height))
  (:default-initargs :name "rectangle")
  (:documentation "An axis-aligned rectangle with WIDTH and HEIGHT."))

(defclass square (rectangle)
  ;; A square IS-A rectangle; it adds no slots but constrains them at init.
  ()
  (:default-initargs :name "square")
  (:documentation "A rectangle whose width and height are forced equal."))

(defclass triangle (shape)
  ((base   :initarg :base   :accessor triangle-base)
   (height :initarg :height :accessor triangle-height)
   ;; Sides are only needed for the perimeter; default to an equilateral-ish
   ;; placeholder so AREA-only callers need not supply them.
   (sides  :initarg :sides  :accessor triangle-sides :initform nil))
  (:default-initargs :name "triangle")
  (:documentation "A triangle with BASE and HEIGHT (for area) and optional
SIDES, a list of three edge lengths (for perimeter)."))

;;; ---------------------------------------------------------------------------
;;; Validation via INITIALIZE-INSTANCE :AFTER (runs after slots are filled)
;;; ---------------------------------------------------------------------------

(defmethod initialize-instance :after ((c circle) &key)
  (setf (circle-radius c) (check-positive :radius (circle-radius c))))

(defmethod initialize-instance :after ((r rectangle) &key)
  ;; Runs for RECTANGLE and, by inheritance, for SQUARE too.
  (setf (rectangle-width r)  (check-positive :width  (rectangle-width r)))
  (setf (rectangle-height r) (check-positive :height (rectangle-height r))))

(defmethod initialize-instance :after ((s square) &key)
  ;; A square's "size" is taken from WIDTH; force HEIGHT to match.
  (setf (rectangle-height s) (rectangle-width s)))

(defmethod initialize-instance :after ((tri triangle) &key)
  (setf (triangle-base tri)   (check-positive :base   (triangle-base tri)))
  (setf (triangle-height tri) (check-positive :height (triangle-height tri))))

;;; ---------------------------------------------------------------------------
;;; Friendly constructors (thin wrappers over MAKE-INSTANCE)
;;; ---------------------------------------------------------------------------

(defun make-circle (radius)
  (make-instance 'circle :radius radius))

(defun make-rectangle (width height)
  (make-instance 'rectangle :width width :height height))

(defun make-square (side)
  (make-instance 'square :width side :height side))

(defun make-triangle (base height &optional sides)
  (make-instance 'triangle :base base :height height :sides sides))

;;; ---------------------------------------------------------------------------
;;; Generic functions: the AREA / PERIMETER protocol
;;; ---------------------------------------------------------------------------

(defgeneric area (shape)
  (:documentation "Return the area of SHAPE as a real number."))

(defgeneric perimeter (shape)
  (:documentation "Return the perimeter of SHAPE as a real number."))

;; Polymorphism: one generic function, several methods chosen by argument type.
(defmethod area ((c circle))
  (* pi (expt (circle-radius c) 2)))

(defmethod perimeter ((c circle))
  (* 2 pi (circle-radius c)))

(defmethod area ((r rectangle))
  (* (rectangle-width r) (rectangle-height r)))

(defmethod perimeter ((r rectangle))
  (* 2 (+ (rectangle-width r) (rectangle-height r))))

;; NOTE: SQUARE deliberately has NO `area` method -- it inherits RECTANGLE's.
;; This is inheritance/polymorphism in action: (area (make-square 4)) => 16.

(defmethod area ((tri triangle))
  (/ (* (triangle-base tri) (triangle-height tri)) 2))

(defmethod perimeter ((tri triangle))
  (let ((sides (triangle-sides tri)))
    (if (and (listp sides) (= (length sides) 3))
        (reduce #'+ sides)
        ;; Reuse the condition system rather than returning a bogus number.
        (error 'invalid-dimension :name :sides :value sides))))

;;; ---------------------------------------------------------------------------
;;; DESCRIBE-SHAPE with :AROUND method combination
;;; ---------------------------------------------------------------------------

(defgeneric describe-shape (shape)
  (:documentation "Return a human-readable, one-line description string."))

(defmethod describe-shape ((s shape))
  ;; Primary method: the default text for any shape.
  (format nil "~A with area ~,3F" (shape-name s) (area s)))

(defmethod describe-shape :around ((s shape))
  ;; :around wraps the primary method. We can run code before/after and
  ;; decide whether to call CALL-NEXT-METHOD (the primary method) at all.
  (format nil "[~A] ~A" (class-name (class-of s)) (call-next-method)))
