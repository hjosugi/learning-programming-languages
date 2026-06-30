"""Self-contained test suite -- standard library only.

No third-party PDF reader is used: source PDFs and PNGs are built from raw
bytes here, and every operation is checked by re-parsing the output with the
toolkit's *own* reader. Page identity is tracked by a unique ``MARK<n>`` token
embedded in each page's content stream, so reorder/select/merge can be checked
by reading the surviving markers back out (decoding the content if compression
added a filter).

Run directly::

    python3 topics/pdf-toolkit/tests/test_pdftoolkit.py
"""

import os
import re
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fixtures import TINY_JPEG  # noqa: E402
from pdftoolkit import images, ops  # noqa: E402
from pdftoolkit.cli import build_parser, main, parse_pages  # noqa: E402
from pdftoolkit.document import Document  # noqa: E402
from pdftoolkit.filters import decode_stream  # noqa: E402
from pdftoolkit.model import Name  # noqa: E402


# --- building PDF / PNG / JPEG fixtures from scratch ------------------------

def build_source_pdf(n_pages, marker_base=0, pad=0, orphan=None):
    """A classic-xref PDF whose page *i* carries token ``MARK<marker_base+i>``
    in an uncompressed content stream. All pages share one font resource.
    ``pad`` appends a repetitive comment so the content compresses noticeably.
    ``orphan`` adds an object that is in the xref table but unreferenced."""
    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    if orphan is not None:
        objs[999] = orphan  # listed in xref, reachable from nothing
    kids = []
    next_num = 4
    for i in range(n_pages):
        content = b"BT /F1 12 Tf 40 700 Td (MARK%d) Tj ET" % (marker_base + i)
        if pad:
            content += b"\n% " + b"PAD" * pad
        content_num = next_num
        page_num = next_num + 1
        next_num += 2
        objs[content_num] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)
        objs[page_num] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % content_num
        )
        kids.append(page_num)
    kids_str = b"[" + b" ".join(b"%d 0 R" % k for k in kids) + b"]"
    objs[2] = b"<< /Type /Pages /Kids %s /Count %d >>" % (kids_str, len(kids))

    out = bytearray(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (num, objs[num])
    xref_pos = len(out)
    size = max(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for num in range(1, size):
        if num in offsets:
            out += b"%010d 00000 n \n" % offsets[num]
        else:
            out += b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_pos)
    return bytes(out)


def _png_chunk(typ, data):
    return len(data).to_bytes(4, "big") + typ + data + zlib.crc32(typ + data).to_bytes(4, "big")


def make_png(w, h, color_type, pixels, palette=None):
    """Assemble an 8-bit, non-interlaced PNG with filter-type 0 rows."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    stride = w * channels
    raw = bytearray()
    for r in range(h):
        raw.append(0)
        raw += pixels[r * stride:(r + 1) * stride]
    out = b"\x89PNG\r\n\x1a\n"
    out += _png_chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") + bytes([8, color_type, 0, 0, 0]))
    if palette is not None:
        out += _png_chunk(b"PLTE", palette)
    out += _png_chunk(b"IDAT", zlib.compress(bytes(raw)))
    out += _png_chunk(b"IEND", b"")
    return out


# --- helpers to read results back ------------------------------------------

def page_markers(data):
    """Marker integer per page of ``data``, in order."""
    doc = Document(data)
    marks = []
    for d, ref, _inh in doc.pages():
        page = doc.resolve(ref)
        contents = doc.resolve(page[Name("Contents")])
        streams = contents if isinstance(contents, list) else [contents]
        blob = b"".join(decode_stream(doc.resolve(s), doc.resolve) for s in streams)
        m = re.search(rb"MARK(\d+)", blob)
        marks.append(int(m.group(1)) if m else None)
    return marks


def page_rotations(data):
    doc = Document(data)
    return [doc.resolve(doc.resolve(ref).get(Name("Rotate"), 0)) for _d, ref, _i in doc.pages()]


def first_image(data):
    doc = Document(data)
    _d, ref, _i = doc.pages()[0]
    page = doc.resolve(ref)
    xobjects = doc.resolve(doc.resolve(page[Name("Resources")])[Name("XObject")])
    return doc.resolve(next(iter(xobjects.values())))


# --- tests -----------------------------------------------------------------

class PageOpsTest(unittest.TestCase):
    def setUp(self):
        self.src = build_source_pdf(5)  # pages carry MARK0..MARK4
        self.doc = lambda: Document(self.src)

    def test_reader_page_count(self):
        self.assertEqual(len(self.doc().pages()), 5)
        self.assertEqual(page_markers(self.src), [0, 1, 2, 3, 4])

    def test_info(self):
        summary = ops.info(self.doc())
        self.assertEqual(summary["pages"], 5)
        self.assertEqual(summary["page_info"][0]["width"], 612)
        self.assertEqual(summary["page_info"][0]["height"], 792)

    def test_select_subset_and_order(self):
        out = ops.select(self.doc(), [1, 3, 5])
        self.assertEqual(page_markers(out), [0, 2, 4])

    def test_select_with_duplicates(self):
        out = ops.select(self.doc(), [2, 2, 1])
        self.assertEqual(page_markers(out), [1, 1, 0])

    def test_reorder(self):
        out = ops.reorder(self.doc(), [5, 4, 3, 2, 1])
        self.assertEqual(page_markers(out), [4, 3, 2, 1, 0])

    def test_reorder_rejects_non_permutation(self):
        with self.assertRaises(ValueError):
            ops.reorder(self.doc(), [1, 2, 3])

    def test_delete(self):
        out = ops.delete(self.doc(), [2, 4])
        self.assertEqual(page_markers(out), [0, 2, 4])

    def test_delete_all_refused(self):
        with self.assertRaises(ValueError):
            ops.delete(self.doc(), [1, 2, 3, 4, 5])

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            ops.select(self.doc(), [99])

    def test_rotate(self):
        out = ops.rotate(self.doc(), [1, 2], 90)
        self.assertEqual(page_rotations(out), [90, 90, 0, 0, 0])

    def test_rotate_accumulates(self):
        once = ops.rotate(self.doc(), [1], 270)
        twice = ops.rotate(Document(once), [1], 180)
        self.assertEqual(page_rotations(twice)[0], 90)  # (270 + 180) % 360

    def test_rotate_rejects_non_multiple_of_90(self):
        with self.assertRaises(ValueError):
            ops.rotate(self.doc(), [1], 45)

    def test_rotate_swaps_reported_dimensions(self):
        out = ops.rotate(self.doc(), [1], 90)
        info = ops.info(Document(out))
        self.assertEqual((info["page_info"][0]["width"], info["page_info"][0]["height"]), (792, 612))

    def test_merge(self):
        a = Document(build_source_pdf(2, marker_base=10))
        b = Document(build_source_pdf(3, marker_base=20))
        out = ops.merge([a, b])
        self.assertEqual(page_markers(out), [10, 11, 20, 21, 22])

    def test_split_per_page(self):
        outs = ops.split(self.doc())
        self.assertEqual(len(outs), 5)
        self.assertEqual([page_markers(o) for o in outs], [[0], [1], [2], [3], [4]])

    def test_split_by_ranges(self):
        outs = ops.split(self.doc(), [[1, 2], [4, 5]])
        self.assertEqual([page_markers(o) for o in outs], [[0, 1], [3, 4]])

    def test_roundtrip_through_own_reader(self):
        out = ops.select(self.doc(), [2, 4])
        self.assertEqual(len(Document(out).pages()), 2)


class CompressTest(unittest.TestCase):
    def test_compress_preserves_pages_and_content(self):
        src = build_source_pdf(8)
        out = ops.compress(Document(src))
        self.assertEqual(page_markers(out), list(range(8)))

    def test_compress_flate_encodes_bulky_streams(self):
        # A large, repetitive content stream must come out Flate-encoded and
        # smaller; the markers must still survive a decode.
        src = build_source_pdf(3, pad=400)
        out = ops.compress(Document(src))
        self.assertLess(len(out), len(src))
        doc = Document(out)
        _d, ref, _i = doc.pages()[0]
        contents = doc.resolve(doc.resolve(ref)[Name("Contents")])
        self.assertEqual(contents.dict.get(Name("Filter")), Name("FlateDecode"))
        self.assertEqual(page_markers(out), [0, 1, 2])

    def test_compress_drops_unreferenced_objects(self):
        # An orphan object holding a NEEDLE that nothing references must be
        # dropped by reachability-based copying.
        needle = b"NEEDLE_ORPHAN_42"
        src = build_source_pdf(2, orphan=b"<< /Junk (%s) >>" % needle)
        self.assertIn(needle, src)
        out = ops.compress(Document(src))
        self.assertNotIn(needle, out)
        self.assertEqual(page_markers(out), [0, 1])


class XrefStreamTest(unittest.TestCase):
    """Build a PDF whose objects live in an object stream addressed by an xref
    stream, then read it back -- the PDF 1.5+ storage path."""

    def _build_xrefstream_pdf(self):
        # Objects 1 (catalog), 3 (font), 5/6 (pages) go inside an object stream
        # (obj 7). Object 2 (Pages) and 4/8 (content streams) stay top-level.
        # Object 9 is the xref stream.
        members = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            5: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 300] "
               b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>",
            6: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 300] "
               b"/Resources << /Font << /F1 3 0 R >> >> /Contents 8 0 R >>",
        }
        order = [1, 3, 5, 6]
        header = b""
        body = b""
        for num in order:
            header += b"%d %d " % (num, len(body))
            body += members[num] + b" "
        first = len(header)
        objstm_raw = header + body
        objstm_data = zlib.compress(objstm_raw)

        c1 = b"BT /F1 12 Tf 20 250 Td (MARK0) Tj ET"
        c2 = b"BT /F1 12 Tf 20 250 Td (MARK1) Tj ET"

        out = bytearray(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        def emit(num, body_bytes):
            off[num] = len(out)
            out.extend(b"%d 0 obj\n%s\nendobj\n" % (num, body_bytes))

        emit(2, b"<< /Type /Pages /Kids [5 0 R 6 0 R] /Count 2 >>")
        emit(4, b"<< /Length %d >>\nstream\n%s\nendstream" % (len(c1), c1))
        emit(8, b"<< /Length %d >>\nstream\n%s\nendstream" % (len(c2), c2))
        emit(7, b"<< /Type /ObjStm /N 4 /First %d /Length %d /Filter /FlateDecode >>\n"
                b"stream\n%s\nendstream" % (first, len(objstm_data), objstm_data))

        # xref stream (obj 9): W=[1,2,1]; entries for objs 0..9.
        # type 1 = (offset, gen); type 2 = (objstm number, index in stream).
        xref_pos = len(out)
        entries = []
        entries.append((0, 0, 0))            # 0 free
        entries.append((2, off[2], 0))       # 1? no -- index by object number
        # Build by object number 0..9 explicitly:
        table = {
            0: (0, 0, 0),
            1: (2, 7, 0),     # in objstm 7, index 0
            2: (1, off[2], 0),
            3: (2, 7, 1),
            4: (1, off[4], 0),
            5: (2, 7, 2),
            6: (2, 7, 3),
            7: (1, off[7], 0),
            8: (1, off[8], 0),
            9: (1, xref_pos, 0),
        }
        packed = bytearray()
        for num in range(10):
            t, a, b = table[num]
            packed += bytes([t]) + a.to_bytes(2, "big") + bytes([b])
        xref_data = zlib.compress(bytes(packed))
        out.extend(
            b"9 0 obj\n<< /Type /XRef /Size 10 /Root 1 0 R /W [1 2 1] "
            b"/Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream\nendobj\n"
            % (len(xref_data), xref_data)
        )
        out.extend(b"startxref\n%d\n%%%%EOF\n" % xref_pos)
        return bytes(out)

    def test_read_objects_from_object_stream(self):
        pdf = self._build_xrefstream_pdf()
        doc = Document(pdf)
        self.assertEqual(len(doc.pages()), 2)
        self.assertEqual(page_markers(pdf), [0, 1])

    def test_ops_on_xrefstream_pdf(self):
        pdf = self._build_xrefstream_pdf()
        out = ops.select(Document(pdf), [2, 1])
        self.assertEqual(page_markers(out), [1, 0])


class ImagesTest(unittest.TestCase):
    def test_png_rgb(self):
        png = make_png(4, 3, 2, bytes([10, 20, 30]) * 12)
        out = images.images_to_pdf([self._tmp(png, ".png")], page="native")
        img = first_image(out)
        self.assertEqual(img.dict[Name("Width")], 4)
        self.assertEqual(img.dict[Name("Height")], 3)
        self.assertEqual(img.dict[Name("ColorSpace")], Name("DeviceRGB"))

    def test_png_rgba_makes_smask(self):
        png = make_png(2, 2, 6, bytes([200, 0, 0, 128]) * 4)
        out = images.images_to_pdf([self._tmp(png, ".png")])
        img = first_image(out)
        self.assertIn(Name("SMask"), img.dict)

    def test_png_gray(self):
        png = make_png(3, 2, 0, bytes([128]) * 6)
        out = images.images_to_pdf([self._tmp(png, ".png")], page="native")
        img = first_image(out)
        self.assertEqual(img.dict[Name("ColorSpace")], Name("DeviceGray"))
        self.assertEqual((img.dict[Name("Width")], img.dict[Name("Height")]), (3, 2))

    def test_png_palette(self):
        palette = bytes([255, 0, 0, 0, 255, 0])  # two colours
        png = make_png(2, 2, 3, bytes([0, 1, 1, 0]), palette=palette)
        out = images.images_to_pdf([self._tmp(png, ".png")])
        img = first_image(out)
        self.assertEqual(img.dict[Name("ColorSpace")], Name("DeviceRGB"))

    def test_jpeg_passthrough(self):
        out = images.images_to_pdf([self._tmp(TINY_JPEG, ".jpg")], page="native")
        img = first_image(out)
        self.assertEqual((img.dict[Name("Width")], img.dict[Name("Height")]), (7, 5))
        self.assertEqual(img.dict[Name("Filter")], Name("DCTDecode"))
        self.assertEqual(img.data, TINY_JPEG)  # bytes embedded verbatim

    def test_a4_page_size(self):
        png = make_png(10, 10, 2, bytes([0, 0, 0]) * 100)
        out = images.images_to_pdf([self._tmp(png, ".png")], page="a4")
        doc = Document(out)
        box = doc.resolve(doc.pages()[0][1])[Name("MediaBox")]
        self.assertEqual([round(float(v)) for v in box], [0, 0, 595, 842])

    def test_multiple_images_multiple_pages(self):
        png = make_png(3, 3, 2, bytes([1, 2, 3]) * 9)
        p = self._tmp(png, ".png")
        out = images.images_to_pdf([p, p, p])
        self.assertEqual(len(Document(out).pages()), 3)

    def test_rejects_unknown_file(self):
        with self.assertRaises(ValueError):
            images.images_to_pdf([self._tmp(b"not an image", ".png")])

    def _tmp(self, data, suffix):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        self.addCleanup(os.remove, path)
        return path


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)
        self.src = os.path.join(self.dir, "src.pdf")
        with open(self.src, "wb") as fh:
            fh.write(build_source_pdf(4))

    def _cleanup(self):
        for root, _dirs, files in os.walk(self.dir, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            os.rmdir(root)

    def _out(self, name):
        return os.path.join(self.dir, name)

    def test_parse_pages(self):
        self.assertEqual(parse_pages("1-3,5,8-10"), [1, 2, 3, 5, 8, 9, 10])
        self.assertEqual(parse_pages("3-1"), [3, 2, 1])
        self.assertEqual(parse_pages("7"), [7])

    def test_parser_builds(self):
        self.assertIsNotNone(build_parser())

    def test_cli_info(self):
        self.assertEqual(main(["info", self.src]), 0)

    def test_cli_select(self):
        out = self._out("sel.pdf")
        self.assertEqual(main(["select", self.src, out, "--pages", "1,3"]), 0)
        self.assertEqual(page_markers(open(out, "rb").read()), [0, 2])

    def test_cli_merge(self):
        out = self._out("merged.pdf")
        self.assertEqual(main(["merge", self.src, self.src, "-o", out]), 0)
        self.assertEqual(len(Document(open(out, "rb").read()).pages()), 8)

    def test_cli_split(self):
        rc = main(["split", self.src, "--outdir", os.path.join(self.dir, "parts")])
        self.assertEqual(rc, 0)
        parts = os.listdir(os.path.join(self.dir, "parts"))
        self.assertEqual(len(parts), 4)

    def test_cli_compress(self):
        out = self._out("comp.pdf")
        self.assertEqual(main(["compress", self.src, out]), 0)
        self.assertEqual(len(Document(open(out, "rb").read()).pages()), 4)

    def test_cli_img2pdf(self):
        png = make_png(5, 5, 2, bytes([9, 9, 9]) * 25)
        png_path = self._out("a.png")
        with open(png_path, "wb") as fh:
            fh.write(png)
        out = self._out("img.pdf")
        self.assertEqual(main(["img2pdf", png_path, "-o", out, "--page", "letter"]), 0)
        self.assertEqual(len(Document(open(out, "rb").read()).pages()), 1)

    def test_cli_reports_error_for_bad_range(self):
        out = self._out("bad.pdf")
        self.assertEqual(main(["select", self.src, out, "--pages", "99"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
