"""pdftoolkit -- a small, dependency-free PDF manipulation library.

Built from scratch on the Python standard library only (``zlib`` is the
heaviest thing it leans on). It parses real PDFs -- classic cross-reference
tables, cross-reference streams, and object streams -- and rewrites them to
reorder, cut, rotate, merge, split, and compress pages, plus assembling images
into a PDF.

Library entry points::

    from pdftoolkit import ops, images
    doc = ops.load("in.pdf")
    open("out.pdf", "wb").write(ops.select(doc, [1, 2, 3]))

CLI: ``python3 -m pdftoolkit --help``.
"""

from . import images, ops
from .document import Document
from .model import Name, Ref, Stream, String

__all__ = ["ops", "images", "Document", "Name", "Ref", "Stream", "String"]
