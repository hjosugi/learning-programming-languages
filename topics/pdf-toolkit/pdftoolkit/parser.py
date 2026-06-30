"""A tokenizer and recursive-descent parser for PDF objects.

The grammar is small. The only genuinely fiddly parts are:

* telling ``12 0 R`` (a reference) apart from three separate numbers -- done
  with two tokens of look-ahead after any non-negative integer; and
* finding where a stream's bytes end -- driven by ``/Length`` when it is known,
  with a scan for ``endstream`` as a fallback for broken files.

The lexer works on raw ``bytes`` and never decodes text encodings; PDF names
and strings are byte sequences and are kept as such (latin-1) until something
higher up decides what they mean.
"""

from __future__ import annotations

from .model import Name, Ref, Stream, String

_WHITESPACE = b"\x00\t\n\f\r "
_DELIM = b"()<>[]{}/%"
_NUM_START = b"+-.0123456789"
_OCTAL = b"01234567"


class Lexer:
    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def _skip_ws(self) -> None:
        d, n = self.data, len(self.data)
        while self.pos < n:
            c = d[self.pos]
            if c in _WHITESPACE:
                self.pos += 1
            elif c == 0x25:  # % comment runs to end of line
                while self.pos < n and d[self.pos] not in b"\r\n":
                    self.pos += 1
            else:
                break

    def next_token(self):
        self._skip_ws()
        d, n = self.data, len(self.data)
        if self.pos >= n:
            return ("eof", None)
        c = d[self.pos]
        if c == 0x2F:  # /
            return self._name()
        if c == 0x28:  # (
            return self._literal_string()
        if c == 0x3C:  # <
            if self.pos + 1 < n and d[self.pos + 1] == 0x3C:
                self.pos += 2
                return ("dict_open", None)
            return self._hex_string()
        if c == 0x3E:  # >
            if self.pos + 1 < n and d[self.pos + 1] == 0x3E:
                self.pos += 2
                return ("dict_close", None)
            self.pos += 1
            return ("keyword", ">")
        if c == 0x5B:
            self.pos += 1
            return ("array_open", None)
        if c == 0x5D:
            self.pos += 1
            return ("array_close", None)
        if c in (0x7B, 0x7D):  # { }  (PostScript-function delimiters)
            self.pos += 1
            return ("keyword", chr(c))
        if c in _NUM_START:
            return self._number()
        return self._word()

    def _name(self):
        d, n = self.data, len(self.data)
        self.pos += 1
        out = bytearray()
        while self.pos < n:
            c = d[self.pos]
            if c in _WHITESPACE or c in _DELIM:
                break
            if c == 0x23 and self.pos + 2 < n:  # #XX hex escape
                try:
                    out.append(int(d[self.pos + 1:self.pos + 3], 16))
                    self.pos += 3
                    continue
                except ValueError:
                    pass
            out.append(c)
            self.pos += 1
        return ("name", Name(out.decode("latin-1")))

    def _number(self):
        d, n = self.data, len(self.data)
        start = self.pos
        self.pos += 1
        while self.pos < n and d[self.pos] in b"+-.0123456789eE":
            self.pos += 1
        s = d[start:self.pos].decode("latin-1")
        try:
            if "." in s or "e" in s or "E" in s:
                return ("num", float(s))
            return ("num", int(s))
        except ValueError:
            try:
                return ("num", float(s))
            except ValueError:
                return ("num", 0)

    def _word(self):
        d, n = self.data, len(self.data)
        start = self.pos
        while self.pos < n and d[self.pos] not in _WHITESPACE and d[self.pos] not in _DELIM:
            self.pos += 1
        if self.pos == start:  # a stray delimiter we do not special-case
            self.pos += 1
            return ("keyword", chr(d[start]))
        w = d[start:self.pos].decode("latin-1")
        if w == "true":
            return ("bool", True)
        if w == "false":
            return ("bool", False)
        if w == "null":
            return ("null", None)
        return ("keyword", w)

    def _literal_string(self):
        d, n = self.data, len(self.data)
        self.pos += 1
        out = bytearray()
        depth = 1
        while self.pos < n:
            c = d[self.pos]
            self.pos += 1
            if c == 0x5C:  # backslash escape
                if self.pos >= n:
                    break
                e = d[self.pos]
                self.pos += 1
                if e == 0x6E:
                    out.append(0x0A)
                elif e == 0x72:
                    out.append(0x0D)
                elif e == 0x74:
                    out.append(0x09)
                elif e == 0x62:
                    out.append(0x08)
                elif e == 0x66:
                    out.append(0x0C)
                elif e in b"()\\":
                    out.append(e)
                elif e in _OCTAL:
                    digits = bytes([e])
                    for _ in range(2):
                        if self.pos < n and d[self.pos] in _OCTAL:
                            digits += bytes([d[self.pos]])
                            self.pos += 1
                    out.append(int(digits, 8) & 0xFF)
                elif e == 0x0D:
                    if self.pos < n and d[self.pos] == 0x0A:
                        self.pos += 1  # line continuation
                elif e == 0x0A:
                    pass  # line continuation
                else:
                    out.append(e)
            elif c == 0x28:
                depth += 1
                out.append(c)
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    break
                out.append(c)
            else:
                out.append(c)
        return ("str", String(bytes(out)))

    def _hex_string(self):
        d, n = self.data, len(self.data)
        self.pos += 1
        hx = bytearray()
        while self.pos < n:
            c = d[self.pos]
            self.pos += 1
            if c == 0x3E:
                break
            if c in _WHITESPACE:
                continue
            hx.append(c)
        if len(hx) % 2:
            hx.append(0x30)  # pad per spec
        return ("str", String(bytes(bytearray.fromhex(hx.decode("latin-1")))))


class Parser:
    """Parses one object starting at the current lexer position."""

    def __init__(self, data: bytes, pos: int = 0, resolver=None):
        self.lex = Lexer(data, pos)
        self.data = data
        self.resolver = resolver

    @property
    def pos(self) -> int:
        return self.lex.pos

    def parse_object(self):
        return self._parse(self.lex.next_token())

    def _parse(self, tok):
        kind, val = tok
        if kind == "num":
            return self._maybe_ref(val)
        if kind in ("name", "str", "bool"):
            return val
        if kind == "null":
            return None
        if kind == "array_open":
            return self._array()
        if kind == "dict_open":
            return self._dict_or_stream()
        if kind == "keyword":
            return val
        if kind == "eof":
            raise EOFError("unexpected end of data while parsing object")
        raise ValueError(f"unexpected token {tok!r}")

    def _maybe_ref(self, first):
        # `first` is a number; `first gen R` is a reference, `first gen obj`
        # introduces an indirect object body. Look ahead, restore on miss.
        if isinstance(first, int) and first >= 0:
            save = self.lex.pos
            t2 = self.lex.next_token()
            if t2[0] == "num" and isinstance(t2[1], int):
                t3 = self.lex.next_token()
                if t3 == ("keyword", "R"):
                    return Ref(first, t2[1])
                if t3 == ("keyword", "obj"):
                    return self.parse_object()
            self.lex.pos = save
        return first

    def _array(self):
        arr = []
        while True:
            tok = self.lex.next_token()
            if tok[0] in ("array_close", "eof"):
                break
            arr.append(self._parse(tok))
        return arr

    def _dict_or_stream(self):
        d = {}
        while True:
            tok = self.lex.next_token()
            if tok[0] in ("dict_close", "eof"):
                break
            if tok[0] != "name":
                continue  # tolerate junk keys
            d[tok[1]] = self.parse_object()
        save = self.lex.pos
        if self.lex.next_token() == ("keyword", "stream"):
            return Stream(d, self._read_stream_data(d))
        self.lex.pos = save
        return d

    def _read_stream_data(self, d) -> bytes:
        data = self.data
        pos = self.lex.pos
        if data[pos:pos + 2] == b"\r\n":
            pos += 2
        elif pos < len(data) and data[pos] == 0x0A:
            pos += 1
        elif pos < len(data) and data[pos] == 0x0D:
            pos += 1
        length = d.get(Name("Length"))
        if isinstance(length, Ref) and self.resolver is not None:
            length = self.resolver(length)
        if isinstance(length, int) and length >= 0:
            raw = data[pos:pos + length]
            j = pos + length
            while j < len(data) and data[j] in b"\r\n \t":
                j += 1
            if data[j:j + 9] == b"endstream":
                self.lex.pos = j + 9
                return raw
        # Fallback: /Length missing or wrong -> scan for the keyword.
        idx = data.find(b"endstream", pos)
        if idx < 0:
            idx = len(data)
        raw = data[pos:idx]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n") or raw.endswith(b"\r"):
            raw = raw[:-1]
        self.lex.pos = idx + 9
        return raw
