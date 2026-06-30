"""Turn JPEG and PNG images into a PDF, one image per page.

JPEG bytes embed directly: PDF speaks ``DCTDecode``, so the compressed data is
stored verbatim and the page just paints it. PNG must be unpacked -- inflate
the IDAT data, undo the row predictors, and (for RGBA/grey+alpha) peel the
alpha channel off into a soft mask -- then re-stored with ``FlateDecode``.

Supported: 8-bit, non-interlaced PNG of colour types greyscale, RGB, RGBA,
grey+alpha, and palette; baseline/progressive JPEG (grey, RGB, CMYK). 16-bit
and interlaced PNGs are rejected with a clear message rather than guessed at.
"""

from __future__ import annotations

import zlib

from .builder import Builder, write_document
from .filters import png_unpredict
from .model import Name, Ref, Stream

PAGE_SIZES = {"a4": (595.276, 841.89), "letter": (612.0, 792.0)}
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


class _Image:
    """A decoded image ready to embed: the XObject dict + data, plus an
    optional greyscale soft-mask (alpha)."""

    def __init__(self, width, height, xdict, data, smask_data=None):
        self.width = width
        self.height = height
        self.dict = xdict
        self.data = data
        self.smask_data = smask_data


def _parse_jpeg(data: bytes) -> _Image:
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG file")
    i, n = 2, len(data)
    while i + 1 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        i += 2
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if i + 2 > n:
            break
        seg = int.from_bytes(data[i:i + 2], "big")
        if marker in _SOF_MARKERS:
            comps = data[i + 7]
            height = int.from_bytes(data[i + 3:i + 5], "big")
            width = int.from_bytes(data[i + 5:i + 7], "big")
            cs = {1: "DeviceGray", 3: "DeviceRGB", 4: "DeviceCMYK"}.get(comps)
            if cs is None:
                raise ValueError(f"unsupported JPEG component count {comps}")
            xdict = {
                Name("Type"): Name("XObject"),
                Name("Subtype"): Name("Image"),
                Name("Width"): width,
                Name("Height"): height,
                Name("ColorSpace"): Name(cs),
                Name("BitsPerComponent"): 8,
                Name("Filter"): Name("DCTDecode"),
            }
            return _Image(width, height, xdict, data)
        i += seg
    raise ValueError("no start-of-frame marker found in JPEG")


def _parse_png(data: bytes) -> _Image:
    if data[:8] != _PNG_SIG:
        raise ValueError("not a PNG file")
    i, n = 8, len(data)
    ihdr = plte = trns = None
    idat = bytearray()
    while i + 8 <= n:
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        chunk = data[i + 8:i + 8 + length]
        i += 12 + length  # length + type + data + crc
        if ctype == b"IHDR":
            ihdr = chunk
        elif ctype == b"PLTE":
            plte = chunk
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"tRNS":
            trns = chunk
        elif ctype == b"IEND":
            break
    if ihdr is None:
        raise ValueError("PNG missing IHDR")
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    depth, color_type, interlace = ihdr[8], ihdr[9], ihdr[12]
    if depth != 8:
        raise ValueError("only 8-bit PNG is supported")
    if interlace != 0:
        raise ValueError("interlaced PNG is not supported")

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"unsupported PNG colour type {color_type}")
    samples = png_unpredict(zlib.decompress(bytes(idat)), channels, 8, width)

    smask = None
    if color_type == 0:
        cs, image = "DeviceGray", samples
    elif color_type == 2:
        cs, image = "DeviceRGB", samples
    elif color_type == 4:  # grey + alpha
        cs = "DeviceGray"
        image = samples[0::2]
        smask = samples[1::2]
    elif color_type == 6:  # RGBA
        cs = "DeviceRGB"
        rgb = bytearray()
        alpha = bytearray()
        for p in range(0, len(samples), 4):
            rgb += samples[p:p + 3]
            alpha.append(samples[p + 3])
        image, smask = bytes(rgb), bytes(alpha)
    else:  # palette
        if plte is None:
            raise ValueError("palette PNG missing PLTE")
        cs = "DeviceRGB"
        rgb = bytearray()
        for idx in samples:
            rgb += plte[idx * 3:idx * 3 + 3]
        image = bytes(rgb)
        if trns is not None:
            alpha = bytearray()
            for idx in samples:
                alpha.append(trns[idx] if idx < len(trns) else 0xFF)
            smask = bytes(alpha)

    xdict = {
        Name("Type"): Name("XObject"),
        Name("Subtype"): Name("Image"),
        Name("Width"): width,
        Name("Height"): height,
        Name("ColorSpace"): Name(cs),
        Name("BitsPerComponent"): 8,
        Name("Filter"): Name("FlateDecode"),
    }
    return _Image(width, height, xdict, zlib.compress(bytes(image), 9),
                  zlib.compress(bytes(smask), 9) if smask is not None else None)


def _decode_image(path: str) -> _Image:
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] == _PNG_SIG:
        return _parse_png(data)
    if data[:2] == b"\xff\xd8":
        return _parse_jpeg(data)
    raise ValueError(f"{path}: unrecognized image (need JPEG or PNG)")


def _placement(img: _Image, page: str, dpi: float):
    """Return (page_w, page_h, draw_w, draw_h, off_x, off_y) in PDF points."""
    img_w = img.width * 72.0 / dpi
    img_h = img.height * 72.0 / dpi
    if page == "native":
        return img_w, img_h, img_w, img_h, 0.0, 0.0
    pw, ph = PAGE_SIZES[page]
    scale = min(pw / img_w, ph / img_h)
    dw, dh = img_w * scale, img_h * scale
    return pw, ph, dw, dh, (pw - dw) / 2, (ph - dh) / 2


def images_to_pdf(paths: list, page: str = "a4", dpi: float = 72.0) -> bytes:
    if not paths:
        raise ValueError("no images given")
    if page not in PAGE_SIZES and page != "native":
        raise ValueError(f"unknown page size {page!r}")

    b = Builder()
    catalog_num = b.alloc()
    pages_num = b.alloc()
    kids = []

    for path in paths:
        img = _decode_image(path)
        if img.smask_data is not None:
            smask_num = b.alloc()
            b.objects[smask_num] = Stream(
                {
                    Name("Type"): Name("XObject"),
                    Name("Subtype"): Name("Image"),
                    Name("Width"): img.width,
                    Name("Height"): img.height,
                    Name("ColorSpace"): Name("DeviceGray"),
                    Name("BitsPerComponent"): 8,
                    Name("Filter"): Name("FlateDecode"),
                },
                img.smask_data,
            )
            img.dict[Name("SMask")] = Ref(smask_num)
        xobj_num = b.alloc()
        b.objects[xobj_num] = Stream(img.dict, img.data)

        pw, ph, dw, dh, ox, oy = _placement(img, page, dpi)
        content = (
            b"q %s 0 0 %s %s %s cm /Im0 Do Q"
            % (_fmt(dw), _fmt(dh), _fmt(ox), _fmt(oy))
        )
        content_num = b.alloc()
        b.objects[content_num] = Stream({}, content)

        page_num = b.alloc()
        b.objects[page_num] = {
            Name("Type"): Name("Page"),
            Name("Parent"): Ref(pages_num),
            Name("MediaBox"): [0, 0, round(pw, 3), round(ph, 3)],
            Name("Resources"): {Name("XObject"): {Name("Im0"): Ref(xobj_num)}},
            Name("Contents"): Ref(content_num),
        }
        kids.append(Ref(page_num))

    b.objects[pages_num] = {
        Name("Type"): Name("Pages"),
        Name("Kids"): kids,
        Name("Count"): len(kids),
    }
    b.objects[catalog_num] = {Name("Type"): Name("Catalog"), Name("Pages"): Ref(pages_num)}
    return write_document(b.objects, catalog_num)


def _fmt(x: float) -> bytes:
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return (s or "0").encode("ascii")
