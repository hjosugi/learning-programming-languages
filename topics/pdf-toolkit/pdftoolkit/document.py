"""Loading a PDF: cross-reference tables, xref streams, object streams.

A :class:`Document` is a lazy view over a file's bytes. It reads the
cross-reference data so it knows *where* every object lives, then parses each
object on demand the first time it is asked for (and caches it). Three storage
schemes are supported, which together cover essentially every real-world file:

* the classic ``xref`` table + ``trailer`` (PDF 1.0-1.4);
* cross-reference *streams* (PDF 1.5+, compressed); and
* *object streams*, where many small objects are packed inside one compressed
  stream.

Incremental updates (``/Prev``) and hybrid-reference files (``/XRefStm``) are
followed. If the cross-reference data is broken, we fall back to scanning the
whole file for ``N G obj`` markers, which recovers most damaged PDFs.
"""

from __future__ import annotations

import re

from .filters import decode_stream
from .model import Name, Ref, Stream
from .parser import Lexer, Parser

_INHERITABLE = (Name("MediaBox"), Name("CropBox"), Name("Resources"), Name("Rotate"))


class Document:
    def __init__(self, data: bytes):
        self.data = data
        self.xref: dict[int, tuple] = {}
        self.trailer: dict = {}
        self._cache: dict[int, object] = {}
        self._load()

    # -- construction -------------------------------------------------------

    @classmethod
    def from_path(cls, path: str) -> "Document":
        with open(path, "rb") as fh:
            return cls(fh.read())

    def _load(self) -> None:
        try:
            idx = self.data.rfind(b"startxref")
            if idx < 0:
                raise ValueError("no startxref")
            start = Parser(self.data, idx + len(b"startxref")).parse_object()
            if not isinstance(start, int):
                raise ValueError("bad startxref offset")
            self._read_xref(start, set())
            if Name("Root") not in self.trailer:
                raise ValueError("no /Root in trailer")
        except Exception:
            # Damaged or unusual file: recover by scanning.
            self._rebuild_by_scan()

    # -- cross reference ----------------------------------------------------

    def _read_xref(self, offset: int, seen: set) -> None:
        if offset in seen or offset < 0 or offset >= len(self.data):
            return
        seen.add(offset)
        tok = Lexer(self.data, offset).next_token()
        if tok == ("keyword", "xref"):
            trailer = self._read_classic_xref(offset)
        else:
            trailer = self._read_xref_stream(offset)
        for k, v in trailer.items():
            self.trailer.setdefault(k, v)
        xrefstm = trailer.get(Name("XRefStm"))
        if isinstance(xrefstm, int):
            self._read_xref(xrefstm, seen)
        prev = trailer.get(Name("Prev"))
        if isinstance(prev, int):
            self._read_xref(prev, seen)

    def _read_classic_xref(self, offset: int) -> dict:
        lex = Lexer(self.data, offset)
        lex.next_token()  # 'xref'
        while True:
            tok = lex.next_token()
            if tok == ("keyword", "trailer"):
                break
            if tok[0] != "num":
                break
            start = tok[1]
            count = lex.next_token()[1]
            for i in range(count):
                off = lex.next_token()[1]
                gen = lex.next_token()[1]
                typ = lex.next_token()[1]
                num = start + i
                if typ == "n" and num not in self.xref:
                    self.xref[num] = ("n", off, gen)
        return Parser(self.data, lex.pos, resolver=self.resolve).parse_object()

    def _read_xref_stream(self, offset: int) -> dict:
        stm = self._parse_indirect_at(offset)
        if not isinstance(stm, Stream):
            raise ValueError("expected an xref stream")
        d = stm.dict
        data = decode_stream(stm, self.resolve)
        w = [self.resolve(x) for x in d[Name("W")]]
        size = self.resolve(d.get(Name("Size"), 0))
        index = d.get(Name("Index"))
        index = [0, size] if index is None else [self.resolve(x) for x in index]
        pos = 0

        def read(width):
            nonlocal pos
            if width == 0:
                return None
            val = int.from_bytes(data[pos:pos + width], "big")
            pos += width
            return val

        for start, count in zip(index[0::2], index[1::2]):
            for i in range(count):
                f0 = read(w[0])
                f1 = read(w[1])
                f2 = read(w[2])
                num = start + i
                typ = 1 if w[0] == 0 else (f0 if f0 is not None else 1)
                if num in self.xref:
                    continue
                if typ == 1:
                    self.xref[num] = ("n", f1, f2 or 0)
                elif typ == 2:
                    self.xref[num] = ("o", f1, f2 or 0)
        return d

    def _rebuild_by_scan(self) -> None:
        self.xref.clear()
        for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", self.data):
            self.xref[int(m.group(1))] = ("n", m.start(), int(m.group(2)))
        self._cache.clear()
        if Name("Root") not in self.trailer:
            for num in self.xref:
                try:
                    obj = self.get(num)
                except Exception:
                    continue
                if isinstance(obj, dict) and obj.get(Name("Type")) == Name("Catalog"):
                    self.trailer[Name("Root")] = Ref(num, 0)
                    break

    # -- object access ------------------------------------------------------

    def _parse_indirect_at(self, offset: int):
        p = Parser(self.data, offset, resolver=self.resolve)
        p.lex.next_token()  # object number
        p.lex.next_token()  # generation
        if p.lex.next_token() != ("keyword", "obj"):
            raise ValueError(f"expected 'obj' at offset {offset}")
        return p.parse_object()

    def get(self, num: int, gen: int = 0):
        if num in self._cache:
            return self._cache[num]
        entry = self.xref.get(num)
        if entry is None:
            return None
        if entry[0] == "n":
            obj = self._parse_indirect_at(entry[1])
        elif entry[0] == "o":
            obj = self._get_from_objstm(entry[1], entry[2])
        else:
            obj = None
        self._cache[num] = obj
        return obj

    def _get_from_objstm(self, stm_num: int, index: int):
        stm = self.get(stm_num)
        if not isinstance(stm, Stream):
            raise ValueError("object stream is not a stream")
        data = decode_stream(stm, self.resolve)
        count = self.resolve(stm.dict[Name("N")])
        first = self.resolve(stm.dict[Name("First")])
        lex = Lexer(data, 0)
        offsets = []
        for _ in range(count):
            lex.next_token()  # member object number
            offsets.append(lex.next_token()[1])
        return Parser(data, first + offsets[index], resolver=self.resolve).parse_object()

    def resolve(self, obj):
        """Follow one indirect reference (non-recursively)."""
        if isinstance(obj, Ref):
            return self.get(obj.num, obj.gen)
        return obj

    # -- pages --------------------------------------------------------------

    def pages(self) -> list:
        """Return ``[(self, page_ref, inherited)]`` in document order.

        ``inherited`` carries only the inheritable attributes the page itself
        does not define, resolved from its ancestors -- so a page can later be
        re-parented under a fresh tree without losing its media box, resources,
        or rotation.
        """
        root = self.resolve(self.trailer.get(Name("Root")))
        if not isinstance(root, dict) or Name("Pages") not in root:
            raise ValueError("PDF has no page tree (/Root /Pages)")
        result: list = []
        visited: set = set()

        def walk(node_ref, inherited):
            node = self.resolve(node_ref)
            if not isinstance(node, dict):
                return
            key = (node_ref.num, node_ref.gen) if isinstance(node_ref, Ref) else None
            if key is not None:
                if key in visited:
                    return
                visited.add(key)
            inh = dict(inherited)
            for k in _INHERITABLE:
                if k in node:
                    inh[k] = node[k]
            kids = self.resolve(node.get(Name("Kids")))
            is_pages = node.get(Name("Type")) == Name("Pages") or (
                isinstance(kids, list) and node.get(Name("Type")) != Name("Page")
            )
            if is_pages and isinstance(kids, list):
                for kid in kids:
                    walk(kid, inh)
            else:
                only_missing = {k: inh[k] for k in _INHERITABLE if k in inh and k not in node}
                result.append((self, node_ref, only_missing))

        walk(root[Name("Pages")], {})
        return result
