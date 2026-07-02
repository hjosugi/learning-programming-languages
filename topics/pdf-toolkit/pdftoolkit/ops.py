"""High-level page operations -- the toolkit's public verbs.

Every function takes loaded :class:`Document` objects and returns the bytes of
a new PDF (or, for ``split``, a list of them). Page numbers in this API are
1-based, matching what a person sees in a viewer.
"""

from __future__ import annotations

from .builder import build_full, build_pages
from .document import Document
from .model import Name


def load(path: str) -> Document:
    return Document.from_path(path)


def _effective_rotate(doc, page_ref, inherited) -> int:
    page = doc.resolve(page_ref)
    rot = page.get(Name("Rotate"), inherited.get(Name("Rotate"), 0))
    rot = doc.resolve(rot)
    return int(rot) % 360 if isinstance(rot, (int, float)) else 0


def _box_size(doc, page_ref, inherited):
    page = doc.resolve(page_ref)
    box = doc.resolve(page.get(Name("MediaBox"), inherited.get(Name("MediaBox"))))
    if not isinstance(box, list) or len(box) != 4:
        return (612.0, 792.0)
    x0, y0, x1, y1 = (doc.resolve(v) for v in box)
    return (abs(x1 - x0), abs(y1 - y0))


def info(doc: Document) -> dict:
    """A summary suitable for printing: page count and per-page size/rotation."""
    pages = doc.pages()
    out = {"pages": len(pages), "page_info": []}
    for i, (d, ref, inh) in enumerate(pages, 1):
        w, h = _box_size(d, ref, inh)
        rot = _effective_rotate(d, ref, inh)
        eff_w, eff_h = (h, w) if rot in (90, 270) else (w, h)
        out["page_info"].append(
            {"page": i, "width": round(eff_w, 2), "height": round(eff_h, 2), "rotate": rot}
        )
    return out


def _specs(pages, indices, overrides_for=None):
    specs = []
    for idx in indices:
        doc, ref, inh = pages[idx]
        ov = overrides_for(doc, ref, inh) if overrides_for else None
        specs.append((doc, ref, inh, ov))
    return specs


def _check_range(pages, numbers):
    n = len(pages)
    for p in numbers:
        if p < 1 or p > n:
            raise ValueError(f"page {p} out of range (document has {n} pages)")


def reorder(doc: Document, order: list) -> bytes:
    """Rearrange pages into ``order`` (a permutation of 1..N)."""
    pages = doc.pages()
    _check_range(pages, order)
    if sorted(order) != list(range(1, len(pages) + 1)):
        raise ValueError("reorder needs every page exactly once; use 'select' for a subset")
    return build_pages(_specs(pages, [p - 1 for p in order]))


def select(doc: Document, wanted: list) -> bytes:
    """Keep only ``wanted`` pages, in the given order (duplicates allowed)."""
    pages = doc.pages()
    _check_range(pages, wanted)
    if not wanted:
        raise ValueError("select needs at least one page")
    return build_pages(_specs(pages, [p - 1 for p in wanted]))


def delete(doc: Document, drop: list) -> bytes:
    """Remove the pages in ``drop``."""
    pages = doc.pages()
    _check_range(pages, drop)
    keep = [i for i in range(len(pages)) if (i + 1) not in set(drop)]
    if not keep:
        raise ValueError("refusing to delete every page")
    return build_pages(_specs(pages, keep))


def rotate(doc: Document, targets: list, angle: int) -> bytes:
    """Rotate ``targets`` by ``angle`` (a multiple of 90, clockwise)."""
    if angle % 90 != 0:
        raise ValueError("angle must be a multiple of 90")
    pages = doc.pages()
    _check_range(pages, targets)
    targets = set(targets)
    specs = []
    for i, (d, ref, inh) in enumerate(pages, 1):
        ov = None
        if i in targets:
            ov = {Name("Rotate"): (_effective_rotate(d, ref, inh) + angle) % 360}
        specs.append((d, ref, inh, ov))
    return build_pages(specs)


def merge(docs: list) -> bytes:
    """Concatenate the pages of several documents into one PDF."""
    if not docs:
        raise ValueError("merge needs at least one document")
    specs = []
    for doc in docs:
        for d, ref, inh in doc.pages():
            specs.append((d, ref, inh, None))
    return build_pages(specs)


def split(doc: Document, ranges: list = None) -> list:
    """Split into multiple PDFs.

    With no ``ranges``, produce one single-page PDF per page. Otherwise each
    range (a list of 1-based page numbers) becomes one output PDF.
    """
    pages = doc.pages()
    if ranges is None:
        ranges = [[i] for i in range(1, len(pages) + 1)]
    outputs = []
    for r in ranges:
        _check_range(pages, r)
        outputs.append(build_pages(_specs(pages, [p - 1 for p in r])))
    return outputs


def compress(doc: Document) -> bytes:
    """Shrink a PDF by dropping unreferenced objects and Flate-encoding
    uncompressed streams. Lossless -- it never touches image samples."""
    return build_full(doc, recompress=True)


def annotate(doc: Document, additions: dict) -> bytes:
    """Add annotations without disturbing existing pages or content.

    ``additions`` maps a 1-based page number to a list of annotation specs
    built by :func:`pdftoolkit.annotations.text_note` /
    :func:`pdftoolkit.annotations.highlight`.
    """
    pages = doc.pages()
    _check_range(pages, list(additions.keys()))
    specs = [(d, ref, inh, None) for d, ref, inh in pages]
    annots_by_index = {page_no - 1: spec_list for page_no, spec_list in additions.items()}
    return build_pages(specs, annots_by_index)
