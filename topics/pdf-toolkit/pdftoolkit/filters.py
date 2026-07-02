"""Stream filters needed to *read* a PDF's plumbing.

We deliberately decode as little as possible. Page content, fonts, and images
are copied through untouched (lossless). The only streams we must decode are
the ones that describe the file's own structure -- cross-reference streams and
object streams (PDF 1.5+). Both use ``FlateDecode`` (zlib, in the standard
library) optionally combined with a PNG/TIFF *predictor*, so that is all this
module implements.

The same PNG un-filtering also powers PNG image embedding in
:mod:`pdftoolkit.images`, which is why ``png_unpredict`` lives here.
"""

from __future__ import annotations

import zlib

from .model import Name, Stream


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def png_unpredict(data: bytes, colors: int, bpc: int, columns: int) -> bytes:
    """Reverse PNG predictors (filter byte per row). 8-bit only."""
    bpp = max(1, (colors * bpc + 7) // 8)
    stride = (colors * bpc * columns + 7) // 8
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    n = len(data)
    while i + 1 + stride <= n:
        ft = data[i]
        i += 1
        row = bytearray(data[i:i + stride])
        i += stride
        for j in range(stride):
            a = row[j - bpp] if j >= bpp else 0
            b = prev[j]
            c = prev[j - bpp] if j >= bpp else 0
            x = row[j]
            if ft == 0:
                r = x
            elif ft == 1:
                r = x + a
            elif ft == 2:
                r = x + b
            elif ft == 3:
                r = x + ((a + b) >> 1)
            elif ft == 4:
                r = x + _paeth(a, b, c)
            else:
                raise ValueError(f"bad PNG filter type {ft}")
            row[j] = r & 0xFF
        out += row
        prev = row
    return bytes(out)


def _tiff_unpredict(data: bytes, colors: int, columns: int) -> bytes:
    stride = colors * columns
    out = bytearray(data)
    for r in range(0, len(out) - stride + 1, stride):
        for j in range(colors, stride):
            out[r + j] = (out[r + j] + out[r + j - colors]) & 0xFF
    return bytes(out)


def _apply_predictor(data: bytes, parms: dict, resolve) -> bytes:
    pred = resolve(parms.get(Name("Predictor"), 1))
    if not pred or pred <= 1:
        return data
    colors = resolve(parms.get(Name("Colors"), 1))
    bpc = resolve(parms.get(Name("BitsPerComponent"), 8))
    columns = resolve(parms.get(Name("Columns"), 1))
    if pred == 2:
        return _tiff_unpredict(data, colors, columns)
    return png_unpredict(data, colors, bpc, columns)


def decode_stream(stream: Stream, resolve) -> bytes:
    """Fully decode a structural stream (FlateDecode + optional predictor).

    ``resolve`` turns an indirect reference into its target so that filter
    parameters stored indirectly still work.
    """
    data = stream.data
    filt = resolve(stream.dict.get(Name("Filter")))
    if filt is None:
        return data
    filters = filt if isinstance(filt, list) else [filt]
    parms = resolve(stream.dict.get(Name("DecodeParms")))
    if not isinstance(parms, list):
        parms = [parms] * len(filters)
    for f, p in zip(filters, parms):
        f = resolve(f)
        if f in (Name("FlateDecode"), Name("Fl")):
            data = zlib.decompress(data)
            p = resolve(p)
            if isinstance(p, dict):
                data = _apply_predictor(data, p, resolve)
        else:
            raise ValueError(f"unsupported filter for structural stream: {f}")
    return data
