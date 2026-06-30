# PDF Toolkit (from scratch)

A small, **dependency-free** PDF manipulation toolkit — the everyday operations
of a lightweight cross-platform PDF editor (think Stirling-PDF / Xodo), built
from scratch on the Python standard library. It parses real PDFs and rewrites
them to reorder, cut, rotate, merge, split, and compress pages, turn images
into a PDF, and add **notes and highlights**. A built-in **tabbed browser app**
opens files in tabs, views them, and annotates them — with optional **Google
Drive** access over plain `urllib`.

Last verified: 2026-06-30

## Why this exists

"Frequently used first, advanced editing later." The operations people actually
reach for every day are *page* operations and format conversion — rearranging,
extracting, rotating, combining, shrinking, and scanning images into a PDF.
None of those require rendering glyphs or rasterizing the page; they only
require understanding the PDF *object graph*. So this lab implements exactly
that core, the way the rest of this repo implements things "from scratch":

- **Pure standard library.** The heaviest dependency is `zlib`, which ships
  with Python. No `pypdf`, no `qpdf`, no native libraries.
- **Cross-platform and lightweight.** It runs anywhere Python runs
  (Windows / macOS / Linux) with nothing to install.
- **Lossless.** Page content, fonts, and images are copied through byte-for-byte.
  The toolkit never re-renders or degrades a page.

A graphical editor (the Xodo-style UI) is the layer that would sit *on top* of
this engine — that is the "advanced, later" part.

## What it does

| Verb | What it does | Stirling/Xodo equivalent |
| --- | --- | --- |
| `info` | page count, page sizes, rotation | document properties |
| `reorder` | rearrange pages into a new order | organize / drag pages |
| `select` | keep a subset of pages (cut/extract) | extract pages |
| `delete` | remove pages | delete pages |
| `rotate` | rotate pages by a multiple of 90° | rotate |
| `merge` | concatenate several PDFs | merge |
| `split` | split into per-page or per-range files | split |
| `img2pdf` | combine JPEG/PNG images into a PDF | image to PDF |
| `compress` | drop unused objects + Flate-encode streams | compress |
| `note` | add a sticky-note comment (memo) | add comment |
| `highlight` | highlight a rectangle (marker) | highlighter |
| `serve` | launch the tabbed browser viewer/editor | the app window |

Notes and highlights are real PDF annotation objects (`/Text`, `/Highlight`):
the page's content is never rewritten, so it stays lossless, and the annotations
ride along through every other operation (compress, reorder, …). Note text is
stored as UTF-16BE, so Japanese (and any other) text is preserved.

## How this is organized

```text
topics/pdf-toolkit/
  pdftoolkit/
    model.py       # the PDF object model (Name/String/Ref/Stream) + serializer
    filters.py     # FlateDecode + PNG/TIFF predictors (only for structural streams)
    parser.py      # tokenizer + recursive-descent object parser
    document.py    # loader: xref tables, xref streams, object streams, page tree
    builder.py     # deep-copy-with-renumbering, the garbage collector, the writer
    ops.py         # page verbs (reorder/select/delete/rotate/merge/split/compress/annotate)
    images.py      # JPEG/PNG -> PDF
    annotations.py # sticky notes + highlights (with appearance streams)
    storage.py     # storage providers: local disk + Google Drive (urllib only)
    app.py         # the tabbed browser viewer/editor (stdlib http.server)
    cli.py         # argparse front end
    __main__.py    # `python3 -m pdftoolkit`
  tests/
    test_pdftoolkit.py  # stdlib-only; builds PDFs/PNGs/JPEG fixtures from scratch
    fixtures.py         # a tiny base64 JPEG so tests need no image library
```

## Run

From this directory (`topics/pdf-toolkit`):

```bash
# inspect
python3 -m pdftoolkit info in.pdf

# reorder pages (a permutation of all pages)
python3 -m pdftoolkit reorder in.pdf out.pdf --order 3,1,2

# cut/extract a subset (ranges allowed: 1-3,5,8-10)
python3 -m pdftoolkit select in.pdf out.pdf --pages 1-3,5

# delete pages
python3 -m pdftoolkit delete in.pdf out.pdf --pages 2,4

# rotate (clockwise, multiple of 90; --pages optional, default all)
python3 -m pdftoolkit rotate in.pdf out.pdf --angle 90 --pages 1-2

# merge several PDFs
python3 -m pdftoolkit merge a.pdf b.pdf c.pdf -o out.pdf

# split into one file per page (or per range)
python3 -m pdftoolkit split in.pdf --outdir parts/
python3 -m pdftoolkit split in.pdf --outdir parts/ --ranges 1-2 3-4

# images -> PDF (a4 | letter | native; --dpi controls native page size)
python3 -m pdftoolkit img2pdf scan1.jpg scan2.png -o out.pdf --page a4

# compress (lossless: garbage-collect + Flate-encode uncompressed streams)
python3 -m pdftoolkit compress in.pdf out.pdf

# add a sticky note (memo) at x,y in PDF points (origin bottom-left)
python3 -m pdftoolkit note in.pdf out.pdf --page 1 --at 100,700 --text "要確認" --color pink

# highlight (marker) a rectangle x0,y0,x1,y1
python3 -m pdftoolkit highlight in.pdf out.pdf --page 1 --rect 72,710,360,730 --color yellow
```

As a library:

```python
from pdftoolkit import ops, images, annotations
doc = ops.load("in.pdf")
open("first3.pdf", "wb").write(ops.select(doc, [1, 2, 3]))
open("scan.pdf", "wb").write(images.images_to_pdf(["a.jpg", "b.png"], page="a4"))
open("annotated.pdf", "wb").write(ops.annotate(doc, {
    1: [annotations.text_note(100, 700, "メモ"),
        annotations.highlight([(72, 710, 360, 730)], color=annotations.COLORS["green"])],
}))
```

## The tabbed app

```bash
python3 -m pdftoolkit serve --dir myfolder      # then open http://127.0.0.1:8000/
```

The page lists the PDFs in `--dir`, opens each in its own **tab**, renders it
with the browser's built-in PDF viewer, and applies notes/highlights through the
engine — saving the edit back to the file. The only runtime is Python's own
`http.server`; the UI is one self-contained HTML page (no JS build, no CDN).

### Google Drive

Drive is a second storage source, spoken over its REST API with **only**
`urllib` — no Google client library. Supply an OAuth2 access token with a Drive
scope and a "drive" source appears in the app:

```bash
export GDRIVE_TOKEN="ya29...."          # an OAuth2 access token (drive scope)
python3 -m pdftoolkit serve --dir myfolder
```

Then `list` / open / save-in-place all work against Drive. Getting the token is
the user's one setup step (any OAuth2 flow — e.g. the OAuth Playground for a
quick try, or your own client for the real thing); everything after that is
plain HTTPS. Storage is pluggable (`storage.py`), so other backends slot in the
same way.

## Test

Standard library only — no third-party packages, no network:

```bash
python3 tests/test_pdftoolkit.py
```

Expected: `58` tests, all passing. The suite builds its own source PDFs, PNGs
(grayscale / RGB / RGBA / palette), and an object-stream + xref-stream PDF
*from raw bytes*, runs every operation (including annotations), exercises the
web app's HTTP endpoints against a live local server, and checks the Drive
adapter with a fake transport (no network). Results are verified by re-parsing
output with the toolkit's own reader — page identity is tracked by a marker
embedded in each page's content stream.

## How it works (the reading order)

A PDF is a graph of typed objects (dictionaries, arrays, streams, numbers,
names, strings) joined by *indirect references* like `12 0 R`. Almost every
operation here is the same move: **start at some pages, copy everything they
reach into a fresh file, and renumber the references.**

1. **`model.py` — the object graph.** Eight Python types stand in for the eight
   PDF types. `encode_object` is the single place that turns any of them back
   into bytes; the writer leans on it, so the on-disk encoding lives in one spot.

2. **`parser.py` — reading objects.** A byte-level lexer plus a recursive-descent
   parser. The two fiddly bits: distinguishing `12 0 R` (a reference) from three
   separate numbers, done with two tokens of look-ahead; and finding where a
   stream's bytes end, driven by `/Length` with a scan for `endstream` as a
   fallback.

3. **`document.py` — finding objects.** The cross-reference data says *where*
   every object lives; objects are then parsed lazily on first use. Three storage
   schemes are handled, together covering essentially every real file: the
   classic `xref` table, cross-reference **streams** (PDF 1.5+), and **object
   streams** (many small objects packed into one compressed stream). Incremental
   updates (`/Prev`) and hybrid files (`/XRefStm`) are followed; a broken xref
   falls back to scanning the file for `N G obj` markers. `pages()` walks the
   page tree and **flattens inherited attributes** (media box, resources,
   rotation) down onto each page so a page can be re-parented safely.

4. **`builder.py` — writing a new file.** `copy_value` deep-copies an object from
   a source document into a fresh, contiguously numbered object table, rewriting
   every reference as it goes and breaking reference cycles. Anything no page
   reaches is simply never copied — which is also how `compress` garbage-collects.
   `/Parent` links are dropped while copying pages so the copy doesn't climb back
   up the old tree; a fresh parent is wired in afterward. `write_document` emits a
   classic xref table and trailer.

5. **`ops.py` — the verbs.** Thin glue: pick/reorder/duplicate the page list, set
   `/Rotate` overrides, concatenate page lists for merge, copy the whole catalog
   for compress, attach annotations to chosen pages.

6. **`filters.py` / `images.py` — bytes in and out.** `filters.py` implements only
   what reading the *plumbing* needs: `FlateDecode` and PNG/TIFF predictors.
   `images.py` embeds JPEGs verbatim (PDF speaks `DCTDecode`) and unpacks PNGs
   (inflate, un-filter, split out alpha into a soft mask) — reusing the same PNG
   predictor code.

7. **`annotations.py` — basic editing.** Notes and highlights are annotation
   *objects* added to a page's `/Annots`, never edits to the content. Highlights
   carry a generated appearance stream (translucent, *Multiply* blend) so they
   show in every viewer. The builder injects them as it copies pages, so they
   ride through every other operation.

8. **`storage.py` / `app.py` — the editor surface.** `app.py` is a `http.server`
   shell: one HTML page with tabs, a file list, the browser's PDF viewer in an
   iframe, and an annotate panel that POSTs to the engine. `storage.py` is the
   pluggable source — local disk, or Google Drive over `urllib`.

## Scope and limitations

Honest about what "common operations first" leaves out:

- **No rendering, and no in-place content editing.** The toolkit does not
  rasterize pages or rewrite existing text/vector content; it adds annotations
  and rearranges objects. The app views PDFs through the *browser's* renderer.
- **Annotations are coordinate-based.** The CLI/app take PDF points (origin
  bottom-left). Click-to-place needs page rendering, so it is the next step for
  the app, not part of this engine.
- **`compress` is conservative and lossless.** It removes unreferenced objects and
  Flate-encodes streams that were stored uncompressed; it does **not** downsample
  images or subset fonts (that is the "advanced, later" work, and is lossy).
  On a tiny, already-optimized file the rewrite can even be a few bytes larger;
  the wins show up on real documents with uncompressed content and redundant
  objects.
- **Image input:** baseline/progressive JPEG (gray/RGB/CMYK) and 8-bit,
  non-interlaced PNG (gray, RGB, RGBA, gray+alpha, palette). 16-bit and
  interlaced PNGs are rejected with a clear message rather than guessed at.
- **Encrypted PDFs are not decrypted.**

## Upgrade path

Each step is additive and keeps the core API:

1. **Click-to-place annotations.** Render page thumbnails (or use `pdf.js`) so
   the app can map a click to PDF points — turning the coordinate form into a
   point-and-drag highlighter.
2. **More annotation types.** Free-text boxes, ink/freehand, underline, and
   strike-out — all the same `/Annots` machinery with different subtypes.
3. **Bookmarks/outlines & links.** Preserve `/Outlines` and remap `/Dest`
   targets through the same reference renumbering when selecting/reordering.
4. **N-up & booklet imposition.** Place several source pages onto one output page
   with a `/XObject` form per source page and a placement matrix.
5. **Drive niceties.** Token refresh, a folder picker, and conflict handling on
   save — building on the `urllib` adapter already here.
6. **Lossy compression.** Re-encode image XObjects (downsample, JPEG) — needs a
   pixel pipeline, so it graduates beyond "stdlib only".

## Exercises

Each builds on the last; run `python3 tests/test_pdftoolkit.py` after each.

1. **`metadata` verb.** Read and set `/Info` (Title/Author) and print it from
   `info`. (Practices: trailer/`/Info`, string objects.)
2. **`select` by step.** Accept `--pages even` / `odd` in the range parser.
   (Practices: the CLI boundary, page indexing.)
3. **`insert` / page move.** Insert one PDF's pages into another at position *k*
   — a small recombination of `merge` + `select`.
4. **Outlines survive `select`.** Copy `/Outlines`, drop entries whose
   destination page was removed, and remap the rest. (Practices: the reference
   graph, reachability.)
5. **TIFF predictor coverage.** Add a test that builds an xref stream using TIFF
   predictor 2 and confirm `filters.py` decodes it. (Practices: predictors.)
