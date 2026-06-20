;;;; load.lisp --- Plain-SBCL loader (no ASDF, no Quicklisp required).
;;;;
;;;; The PRIMARY workflow in this repo is offline `sbcl --script`, so we cannot
;;;; assume ASDF is configured to find this system.  This file loads the source
;;;; files in dependency order relative to ITS OWN location, which makes the
;;;; project runnable from any working directory.
;;;;
;;;; *LOAD-PATHNAME* is the path of the file currently being loaded; we take its
;;;; directory and merge each source name against it.

(let ((here (or *load-pathname* *compile-file-pathname*)))
  (flet ((src (name)
           (merge-pathnames name here)))
    ;; Order matters: packages -> conditions -> classes -> functions -> macros.
    (dolist (file '("packages.lisp"
                    "conditions.lisp"
                    "shapes.lisp"
                    "scene.lisp"
                    "macros.lisp"))
      (load (src file)))))
