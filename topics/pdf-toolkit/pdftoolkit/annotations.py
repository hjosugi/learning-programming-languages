"""Basic editing: annotations (sticky notes and highlights).

These are the everyday "編集" actions -- jot a note, swipe a highlighter -- and
in PDF they are *annotation objects*, not changes to the page's content. Each
page carries an ``/Annots`` array of annotation dictionaries; adding an
annotation means adding one such object and appending its reference. The page's
original content is never touched, so this stays as lossless as every other
operation in the toolkit.

Two kinds are implemented:

* **text note** (``/Subtype /Text``) -- a sticky-note icon with a comment;
* **highlight** (``/Subtype /Highlight``) -- a marker swipe over a rectangle,
  with a generated appearance stream (translucent, *Multiply* blend) so it is
  visible in every viewer, not just ones that synthesize appearances.

Note text is stored as UTF-16BE so notes in any language (including Japanese)
survive. Coordinates are PDF user-space points with the origin at the
bottom-left of the page.
"""

from __future__ import annotations

from .model import Name, Ref, Stream, String

# A few friendly highlighter colours (RGB, 0..1).
COLORS = {
    "yellow": (1.0, 0.92, 0.23),
    "green": (0.40, 0.93, 0.40),
    "pink": (1.0, 0.45, 0.65),
    "blue": (0.45, 0.70, 1.0),
    "orange": (1.0, 0.65, 0.15),
}


def _text_string(s: str) -> String:
    """Encode text as a PDF UTF-16BE string (BOM-prefixed)."""
    return String(b"\xfe\xff" + s.encode("utf-16-be"))


def text_note(x, y, contents, color=(1.0, 0.92, 0.23), title="", icon="Note") -> dict:
    """A sticky-note annotation whose icon sits at ``(x, y)``."""
    return {
        "kind": "text",
        "rect": [x, y, x + 20, y + 20],
        "contents": contents,
        "color": color,
        "title": title,
        "icon": icon,
    }


def highlight(quads, color=(1.0, 0.92, 0.23), contents="") -> dict:
    """A highlight over one or more rectangles.

    ``quads`` is a list of ``(x0, y0, x1, y1)`` rectangles in page points.
    """
    return {"kind": "highlight", "quads": list(quads), "color": color, "contents": contents}


def _n(v) -> str:
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return s or "0"


def build_annotation(builder, page_ref: Ref, spec: dict) -> Ref:
    """Create the objects for one annotation in ``builder`` and return its Ref.

    ``builder`` is a :class:`pdftoolkit.builder.Builder`; we use its ``alloc``
    and ``objects`` directly so annotations slot into the same object table as
    the copied pages.
    """
    color = [round(float(c), 4) for c in spec.get("color", (1, 1, 0))]
    contents = spec.get("contents") or ""

    if spec["kind"] == "text":
        x0, y0, x1, y1 = spec["rect"]
        annot = {
            Name("Type"): Name("Annot"),
            Name("Subtype"): Name("Text"),
            Name("Rect"): [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
            Name("Contents"): _text_string(contents),
            Name("P"): page_ref,
            Name("Name"): Name(spec.get("icon", "Note")),
            Name("C"): color,
            Name("Open"): False,
        }
        if spec.get("title"):
            annot[Name("T")] = _text_string(spec["title"])
        num = builder.alloc()
        builder.objects[num] = annot
        return Ref(num)

    # highlight
    quads = spec["quads"]
    if not quads:
        raise ValueError("highlight needs at least one rectangle")
    quad_points = []
    xs, ys = [], []
    draw_lines = [f"{_n(color[0])} {_n(color[1])} {_n(color[2])} rg", "/GS gs"]
    for x0, y0, x1, y1 in quads:
        lo_x, hi_x = sorted((x0, x1))
        lo_y, hi_y = sorted((y0, y1))
        # QuadPoints order: upper-left, upper-right, lower-left, lower-right.
        quad_points += [lo_x, hi_y, hi_x, hi_y, lo_x, lo_y, hi_x, lo_y]
        xs += [lo_x, hi_x]
        ys += [lo_y, hi_y]
        draw_lines.append(f"{_n(lo_x)} {_n(lo_y)} {_n(hi_x - lo_x)} {_n(hi_y - lo_y)} re")
        draw_lines.append("f")
    rect = [min(xs), min(ys), max(xs), max(ys)]

    form = Stream(
        {
            Name("Type"): Name("XObject"),
            Name("Subtype"): Name("Form"),
            Name("BBox"): [round(v, 3) for v in rect],
            Name("Resources"): {
                Name("ExtGState"): {
                    Name("GS"): {
                        Name("Type"): Name("ExtGState"),
                        Name("ca"): 0.4,
                        Name("BM"): Name("Multiply"),
                    }
                }
            },
        },
        "\n".join(draw_lines).encode("latin-1"),
    )
    form_num = builder.alloc()
    builder.objects[form_num] = form

    annot = {
        Name("Type"): Name("Annot"),
        Name("Subtype"): Name("Highlight"),
        Name("Rect"): [round(v, 3) for v in rect],
        Name("QuadPoints"): [round(v, 3) for v in quad_points],
        Name("C"): color,
        Name("P"): page_ref,
        Name("AP"): {Name("N"): Ref(form_num)},
    }
    if contents:
        annot[Name("Contents")] = _text_string(contents)
    num = builder.alloc()
    builder.objects[num] = annot
    return Ref(num)
