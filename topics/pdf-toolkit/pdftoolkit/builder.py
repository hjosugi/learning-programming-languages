"""Assembling a new PDF from pieces of one or more source documents.

Everything that rearranges pages -- reorder, select, delete, rotate, merge,
split -- funnels through :func:`build_pages`. The core trick is a *deep copy
that renumbers references*: starting from a page, every object it transitively
points at (content, fonts, image XObjects, ...) is copied into a fresh object
table with new, contiguous numbers, and every ``Ref`` is rewritten to match.
Objects nothing references simply never get copied, so this same machinery is
also how :func:`build_full` garbage-collects during compression.

``/Parent`` links are dropped while copying pages so the copy does not walk
back up into the original page tree; a fresh parent is wired in afterwards.
"""

from __future__ import annotations

import hashlib
import zlib

from .model import Name, Ref, Stream, String, encode_object


class Builder:
    def __init__(self):
        self.objects: dict[int, object] = {}
        self._counter = 0

    def alloc(self) -> int:
        self._counter += 1
        return self._counter


def copy_value(builder: Builder, doc, val, ref_map: dict, skip_parent: bool):
    """Copy ``val`` (from ``doc``) into ``builder``, renumbering references.

    ``ref_map`` is keyed by ``(id(doc), num, gen)`` so the same object is
    copied once even when reached by several paths, and so distinct source
    documents never collide during a merge.
    """
    if isinstance(val, Ref):
        key = (id(doc), val.num, val.gen)
        if key in ref_map:
            return ref_map[key]
        new_num = builder.alloc()
        ref_map[key] = Ref(new_num)  # register before recursing to break cycles
        target = doc.get(val.num, val.gen)
        builder.objects[new_num] = copy_value(builder, doc, target, ref_map, skip_parent)
        return ref_map[key]
    if isinstance(val, Stream):
        d = {}
        for k, v in val.dict.items():
            if k == "Length":
                continue  # recomputed on write
            d[k] = copy_value(builder, doc, v, ref_map, skip_parent)
        return Stream(d, val.data)
    if isinstance(val, dict):
        d = {}
        for k, v in val.items():
            if skip_parent and k == "Parent":
                continue
            d[k] = copy_value(builder, doc, v, ref_map, skip_parent)
        return d
    if isinstance(val, list):
        return [copy_value(builder, doc, x, ref_map, skip_parent) for x in val]
    return val


def write_document(objects: dict, root_num: int, info_num=None) -> bytes:
    """Serialize an object table with a classic cross-reference table."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num
        out += encode_object(objects[num])
        out += b"\nendobj\n"

    xref_pos = len(out)
    size = (max(objects) + 1) if objects else 1
    out += b"xref\n0 %d\n" % size
    out += b"0000000000 65535 f \n"
    for num in range(1, size):
        if num in offsets:
            out += b"%010d 00000 n \n" % offsets[num]
        else:
            out += b"0000000000 65535 f \n"

    ident = hashlib.md5(b"%d:%d" % (size, xref_pos)).hexdigest().encode("ascii")
    trailer = {Name("Size"): size, Name("Root"): Ref(root_num)}
    if info_num is not None:
        trailer[Name("Info")] = Ref(info_num)
    trailer[Name("ID")] = [String(ident), String(ident)]
    out += b"trailer\n" + encode_object(trailer) + b"\n"
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos
    return bytes(out)


def _finalize_page(copied: dict) -> dict:
    if Name("Type") not in copied:
        copied[Name("Type")] = Name("Page")
    if Name("Resources") not in copied:
        copied[Name("Resources")] = {}
    if Name("MediaBox") not in copied:
        copied[Name("MediaBox")] = [0, 0, 612, 792]  # US Letter fallback
    return copied


def build_pages(page_specs: list) -> bytes:
    """Build a PDF from ``[(doc, page_ref, inherited, overrides)]``.

    ``inherited`` supplies attributes the page omits; ``overrides`` forcibly
    replaces attributes (used by rotate). Pages keep their original content
    untouched.
    """
    b = Builder()
    catalog_num = b.alloc()
    pages_num = b.alloc()
    ref_map: dict = {}
    kids: list = []

    for doc, page_ref, inherited, overrides in page_specs:
        key = (id(doc), page_ref.num, page_ref.gen) if isinstance(page_ref, Ref) else None
        new_num = b.alloc()
        if key is not None:
            ref_map[key] = Ref(new_num)  # so back-references (e.g. /P) resolve here
        page_obj = doc.resolve(page_ref)
        copied = {}
        for k, v in page_obj.items():
            if k == "Parent":
                continue
            copied[k] = copy_value(b, doc, v, ref_map, skip_parent=True)
        for k, v in inherited.items():
            if k not in copied:
                copied[k] = copy_value(b, doc, v, ref_map, skip_parent=True)
        for k, v in (overrides or {}).items():
            copied[k] = v
        _finalize_page(copied)
        copied[Name("Parent")] = Ref(pages_num)
        b.objects[new_num] = copied
        kids.append(Ref(new_num))

    b.objects[pages_num] = {
        Name("Type"): Name("Pages"),
        Name("Kids"): kids,
        Name("Count"): len(kids),
    }
    b.objects[catalog_num] = {Name("Type"): Name("Catalog"), Name("Pages"): Ref(pages_num)}
    return write_document(b.objects, catalog_num)


def build_full(doc, recompress: bool = True) -> bytes:
    """Copy a whole document from its ``/Root`` (used by compress).

    Because the copy follows references from the catalog, anything unreachable
    is dropped. With ``recompress`` set, streams stored uncompressed are
    Flate-encoded. ``/Parent`` links are preserved so the original page tree
    stays intact.
    """
    b = Builder()
    ref_map: dict = {}
    root_ref = doc.trailer.get(Name("Root"))
    new_root = copy_value(b, doc, root_ref, ref_map, skip_parent=False)
    info_ref = doc.trailer.get(Name("Info"))
    new_info = copy_value(b, doc, info_ref, ref_map, skip_parent=False) if info_ref else None

    if recompress:
        for num, obj in b.objects.items():
            if isinstance(obj, Stream) and Name("Filter") not in obj.dict:
                packed = zlib.compress(obj.data, 9)
                if len(packed) < len(obj.data):
                    obj.dict[Name("Filter")] = Name("FlateDecode")
                    b.objects[num] = Stream(obj.dict, packed)

    return write_document(b.objects, new_root.num, new_info.num if new_info else None)
