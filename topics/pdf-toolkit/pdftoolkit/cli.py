"""Command-line front end. Run ``python3 -m pdftoolkit --help``.

Each subcommand maps to one verb in :mod:`pdftoolkit.ops` (plus ``img2pdf``
from :mod:`pdftoolkit.images`). Page selections accept ranges like
``1-3,5,8-10`` and are always 1-based.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import annotations, images, ops


def parse_pages(spec: str) -> list:
    """Parse ``"1-3,5,8-10"`` into ``[1, 2, 3, 5, 8, 9, 10]``."""
    result = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            step = 1 if hi >= lo else -1
            result.extend(range(lo, hi + step, step))
        else:
            result.append(int(part))
    return result


def parse_color(spec: str):
    """Parse ``yellow`` (a named colour) or ``r,g,b`` (each 0..1)."""
    if spec in annotations.COLORS:
        return annotations.COLORS[spec]
    parts = [float(x) for x in spec.split(",")]
    if len(parts) != 3:
        raise ValueError(f"colour must be a name {sorted(annotations.COLORS)} or r,g,b")
    return tuple(parts)


def parse_rect(spec: str):
    parts = [float(x) for x in spec.split(",")]
    if len(parts) != 4:
        raise ValueError("rect must be x0,y0,x1,y1")
    return parts


def _write(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def _cmd_info(args) -> int:
    summary = ops.info(ops.load(args.input))
    print(f"{args.input}: {summary['pages']} page(s)")
    for p in summary["page_info"]:
        rot = f", rotated {p['rotate']}deg" if p["rotate"] else ""
        print(f"  page {p['page']}: {p['width']} x {p['height']} pt{rot}")
    return 0


def _cmd_reorder(args) -> int:
    _write(args.output, ops.reorder(ops.load(args.input), parse_pages(args.order)))
    print(f"wrote {args.output}")
    return 0


def _cmd_select(args) -> int:
    _write(args.output, ops.select(ops.load(args.input), parse_pages(args.pages)))
    print(f"wrote {args.output}")
    return 0


def _cmd_delete(args) -> int:
    _write(args.output, ops.delete(ops.load(args.input), parse_pages(args.pages)))
    print(f"wrote {args.output}")
    return 0


def _cmd_rotate(args) -> int:
    doc = ops.load(args.input)
    targets = parse_pages(args.pages) if args.pages else list(range(1, ops.info(doc)["pages"] + 1))
    _write(args.output, ops.rotate(doc, targets, args.angle))
    print(f"wrote {args.output}")
    return 0


def _cmd_merge(args) -> int:
    _write(args.output, ops.merge([ops.load(p) for p in args.inputs]))
    print(f"wrote {args.output}")
    return 0


def _cmd_split(args) -> int:
    doc = ops.load(args.input)
    ranges = [parse_pages(r) for r in args.ranges] if args.ranges else None
    outputs = ops.split(doc, ranges)
    os.makedirs(args.outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.input))[0]
    for i, data in enumerate(outputs, 1):
        path = os.path.join(args.outdir, f"{stem}-{i:03d}.pdf")
        _write(path, data)
        print(f"wrote {path}")
    return 0


def _cmd_img2pdf(args) -> int:
    _write(args.output, images.images_to_pdf(args.images, page=args.page, dpi=args.dpi))
    print(f"wrote {args.output}")
    return 0


def _cmd_note(args) -> int:
    x, y = (float(v) for v in args.at.split(","))
    spec = annotations.text_note(x, y, args.text, color=parse_color(args.color), title=args.title)
    _write(args.output, ops.annotate(ops.load(args.input), {args.page: [spec]}))
    print(f"wrote {args.output}")
    return 0


def _cmd_highlight(args) -> int:
    spec = annotations.highlight([parse_rect(args.rect)], color=parse_color(args.color),
                                 contents=args.text or "")
    _write(args.output, ops.annotate(ops.load(args.input), {args.page: [spec]}))
    print(f"wrote {args.output}")
    return 0


def _cmd_serve(args) -> int:
    from .app import main as app_main
    argv = ["--dir", args.dir, "--host", args.host, "--port", str(args.port)]
    if args.drive_token:
        argv += ["--drive-token", args.drive_token]
    return app_main(argv)


def _cmd_compress(args) -> int:
    before = os.path.getsize(args.input)
    data = ops.compress(ops.load(args.input))
    _write(args.output, data)
    after = len(data)
    pct = (1 - after / before) * 100 if before else 0
    print(f"wrote {args.output}: {before} -> {after} bytes ({pct:.1f}% smaller)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pdftoolkit",
        description="A small, dependency-free PDF toolkit (reorder, cut, "
        "rotate, merge, split, images->PDF, compress).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("info", help="show page count and page sizes")
    s.add_argument("input")
    s.set_defaults(func=_cmd_info)

    s = sub.add_parser("reorder", help="rearrange pages, e.g. --order 3,1,2")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--order", required=True)
    s.set_defaults(func=_cmd_reorder)

    s = sub.add_parser("select", help="keep a subset, e.g. --pages 1-3,5")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--pages", required=True)
    s.set_defaults(func=_cmd_select)

    s = sub.add_parser("delete", help="remove pages, e.g. --pages 2,4")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--pages", required=True)
    s.set_defaults(func=_cmd_delete)

    s = sub.add_parser("rotate", help="rotate pages clockwise by a multiple of 90")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--angle", type=int, required=True)
    s.add_argument("--pages", help="default: all pages")
    s.set_defaults(func=_cmd_rotate)

    s = sub.add_parser("merge", help="concatenate several PDFs")
    s.add_argument("inputs", nargs="+")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=_cmd_merge)

    s = sub.add_parser("split", help="split into separate PDFs")
    s.add_argument("input")
    s.add_argument("--outdir", default=".")
    s.add_argument("--ranges", nargs="*", help="e.g. 1-2 3-4 (default: one file per page)")
    s.set_defaults(func=_cmd_split)

    s = sub.add_parser("img2pdf", help="combine JPEG/PNG images into one PDF")
    s.add_argument("images", nargs="+")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--page", default="a4", help="a4 | letter | native")
    s.add_argument("--dpi", type=float, default=72.0)
    s.set_defaults(func=_cmd_img2pdf)

    s = sub.add_parser("note", help="add a sticky-note comment at x,y (PDF points, origin bottom-left)")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--at", required=True, metavar="X,Y")
    s.add_argument("--text", required=True)
    s.add_argument("--title", default="")
    s.add_argument("--color", default="yellow")
    s.set_defaults(func=_cmd_note)

    s = sub.add_parser("highlight", help="highlight a rectangle x0,y0,x1,y1 (PDF points)")
    s.add_argument("input")
    s.add_argument("output")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--rect", required=True, metavar="X0,Y0,X1,Y1")
    s.add_argument("--text", default="")
    s.add_argument("--color", default="yellow")
    s.set_defaults(func=_cmd_highlight)

    s = sub.add_parser("compress", help="garbage-collect and Flate-compress")
    s.add_argument("input")
    s.add_argument("output")
    s.set_defaults(func=_cmd_compress)

    s = sub.add_parser("serve", help="launch the tabbed browser viewer/editor")
    s.add_argument("--dir", default=".", help="folder of PDFs to serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--drive-token", default=os.environ.get("GDRIVE_TOKEN"))
    s.set_defaults(func=_cmd_serve)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, EOFError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
