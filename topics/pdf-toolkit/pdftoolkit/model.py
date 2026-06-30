"""The PDF object model and a serializer.

A PDF file is, underneath the binary framing, a small graph of typed objects:
booleans, numbers, names, strings, arrays, dictionaries, streams, and
*indirect references* that point from one object to another. This module
defines just enough Python types to represent that graph faithfully and to
write it back out as bytes.

The mapping we use:

    PDF type        Python representation
    ------------    ---------------------
    boolean         bool
    number          int / float
    null            None
    name  /Foo      Name("Foo")        (a str subclass)
    string (...)    String(b"...")     (wraps raw bytes)
    array  [ ... ]  list
    dict << ... >>  dict with Name keys
    stream          Stream(dict, raw_bytes)
    12 0 R          Ref(12, 0)

`encode_object` is the single source of truth for turning any of these back
into bytes; the writer relies on it so the encoding lives in one place.
"""

from __future__ import annotations


class Name(str):
    """A PDF name such as ``/Type``. Stored without the leading slash.

    Subclassing ``str`` means name keys compare and hash like the plain
    string, so ``d[Name("Type")]`` and ``d.get("Type")`` reach the same value.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Name({str.__repr__(self)})"


class String:
    """A PDF string. Holds the *decoded* raw bytes (escapes already resolved)."""

    __slots__ = ("value",)

    def __init__(self, value: bytes):
        if isinstance(value, str):
            value = value.encode("latin-1")
        self.value = bytes(value)

    def __eq__(self, other) -> bool:
        return isinstance(other, String) and other.value == self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"String({self.value!r})"


class Ref:
    """An indirect reference ``num gen R``."""

    __slots__ = ("num", "gen")

    def __init__(self, num: int, gen: int = 0):
        self.num = num
        self.gen = gen

    def __eq__(self, other) -> bool:
        return isinstance(other, Ref) and other.num == self.num and other.gen == self.gen

    def __hash__(self) -> int:
        return hash((self.num, self.gen))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Ref({self.num}, {self.gen})"


class Stream:
    """A stream object: a dictionary plus a blob of (still-encoded) bytes.

    ``data`` is kept exactly as it sits in the file. Reordering or merging
    pages never needs to decode content, so the bytes pass through untouched
    and lossless. Only the cross-reference and object streams are ever decoded
    (see :mod:`pdftoolkit.filters`).
    """

    __slots__ = ("dict", "data")

    def __init__(self, d: dict, data: bytes):
        self.dict = d
        self.data = bytes(data)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Stream({self.dict!r}, {len(self.data)} bytes)"


# --- serialization ---------------------------------------------------------

_NAME_REGULAR = set(range(0x21, 0x7F)) - set(b"()<>[]{}/%#")


def encode_name(name: str) -> bytes:
    out = bytearray(b"/")
    for ch in name.encode("latin-1"):
        if ch in _NAME_REGULAR:
            out.append(ch)
        else:
            out += b"#%02X" % ch
    return bytes(out)


def encode_string(value: bytes) -> bytes:
    out = bytearray(b"(")
    for c in value:
        if c in (0x28, 0x29, 0x5C):  # ( ) \
            out += b"\\" + bytes([c])
        elif c == 0x0A:
            out += b"\\n"
        elif c == 0x0D:
            out += b"\\r"
        elif c == 0x09:
            out += b"\\t"
        elif c < 0x20 or c > 0x7E:
            out += b"\\%03o" % c
        else:
            out.append(c)
    out += b")"
    return bytes(out)


def _encode_number(x) -> bytes:
    if isinstance(x, int):
        return str(x).encode("latin-1")
    s = repr(float(x))
    if "e" in s or "E" in s:
        s = f"{x:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("", "-0"):
        s = "0"
    return s.encode("latin-1")


def encode_object(obj) -> bytes:
    """Serialize a single PDF value to bytes.

    Streams always get a freshly computed ``/Length`` and any indirect
    ``/Length`` from the source is dropped, so the written length can never
    drift from the actual data.
    """
    if isinstance(obj, bool):
        return b"true" if obj else b"false"
    if obj is None:
        return b"null"
    if isinstance(obj, (int, float)):
        return _encode_number(obj)
    if isinstance(obj, Name):
        return encode_name(obj)
    if isinstance(obj, String):
        return encode_string(obj.value)
    if isinstance(obj, Ref):
        return b"%d %d R" % (obj.num, obj.gen)
    if isinstance(obj, list):
        return b"[" + b" ".join(encode_object(x) for x in obj) + b"]"
    if isinstance(obj, Stream):
        d = {k: v for k, v in obj.dict.items() if k != "Length"}
        d[Name("Length")] = len(obj.data)
        return encode_object(d) + b"\nstream\n" + obj.data + b"\nendstream"
    if isinstance(obj, dict):
        parts = bytearray(b"<<")
        for k, v in obj.items():
            parts += encode_name(k) + b" " + encode_object(v)
        parts += b">>"
        return bytes(parts)
    if isinstance(obj, str):  # a bare name used as a value (rare)
        return encode_name(obj)
    raise TypeError(f"cannot encode {type(obj).__name__}: {obj!r}")
