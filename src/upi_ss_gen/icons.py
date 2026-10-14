"""Vector-ish glyphs drawn with PIL primitives. All take (canvas, cx, cy, r, color).
"""

from __future__ import annotations

WHITE = (255, 255, 255)


# --------------------------------------------------------------------------- #
# Status glyphs
# --------------------------------------------------------------------------- #
# Every glyph is expressed as a fraction of the circle radius so the same
# function works for a 90px hero badge and a 36px inline bubble. Fixed pixel
# offsets made small badges render the glyph outside the circle, invisible
# against the background.
def tick(c, cx, cy, r, color):
    w = max(3, r * 0.155)
    c.line([cx - r * 0.47, cy, cx - r * 0.11, cy + r * 0.40], fill=color, width=w)
    c.line([cx - r * 0.11, cy + r * 0.40, cx + r * 0.53, cy - r * 0.38],
           fill=color, width=w)


def cross(c, cx, cy, r, color):
    w = max(3, r * 0.155)
    o = r * 0.42
    c.line([cx - o, cy - o, cx + o, cy + o], fill=color, width=w)
    c.line([cx + o, cy - o, cx - o, cy + o], fill=color, width=w)


def clock(c, cx, cy, r, color):
    w = max(3, r * 0.13)
    k = r * 0.49
    c.ellipse([cx - k, cy - k, cx + k, cy + k], outline=color, width=w)
    c.line([cx, cy - r * 0.29, cx, cy + r * 0.04], fill=color, width=w)
    c.line([cx, cy + r * 0.04, cx + r * 0.27, cy + r * 0.18], fill=color, width=w)


def undo(c, cx, cy, r, color):
    """Counter-clockwise arrow -- the refund / reversed affordance."""
    w = max(3, r * 0.13)
    k = r * 0.51
    c.arc([cx - k, cy - k, cx + k, cy + k], start=140, end=430, fill=color, width=w)
    c.polygon([(cx - r * 0.58, cy - r * 0.60),
               (cx - r * 0.18, cy - r * 0.49),
               (cx - r * 0.51, cy - r * 0.22)], fill=color)


def dots(c, cx, cy, r, color):
    """Three dots tapering in size -- a 'still working' indicator."""
    for dy, k in ((-0.38, 0.18), (0.0, 0.145), (0.38, 0.11)):
        d = r * k
        c.ellipse([cx - d, cy + r * dy - d, cx + d, cy + r * dy + d], fill=color)


STATUS_GLYPHS = {"tick": tick, "cross": cross, "clock": clock, "undo": undo,
                 "dots": dots}


def draw_status_glyph(c, glyph, cx, cy, r, color):
    STATUS_GLYPHS[glyph](c, cx, cy, r, color)


# --------------------------------------------------------------------------- #
# Avatars & affordances
# --------------------------------------------------------------------------- #
def avatar(c, cx, cy, r, bg, fg):
    """Generic person silhouette in a filled circle: head dome + shoulders."""
    c.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    head_r = r * 0.27
    c.ellipse([cx - head_r, cy - r * 0.34 - head_r,
               cx + head_r, cy - r * 0.34 + head_r], fill=fg)
    # shoulders: upper half of an ellipse, sized to stay inside the circle
    w, top = r * 0.66, cy + r * 0.06
    c.pieslice([cx - w, top, cx + w, top + 2 * w], 0, 180, fill=fg)


def chevron(c, cx, cy, size, color, width=7, direction="down"):
    half = size // 2
    if direction == "down":
        c.line([cx - half, cy - half // 2, cx, cy + half // 2], fill=color, width=width)
        c.line([cx, cy + half // 2, cx + half, cy - half // 2], fill=color, width=width)
    else:
        c.line([cx - half, cy + half // 2, cx, cy - half // 2], fill=color, width=width)
        c.line([cx, cy - half // 2, cx + half, cy + half // 2], fill=color, width=width)


def back_arrow(c, x, cy, color, width=8):
    """Horizontal shaft with a chevron head on the left."""
    c.line([x, cy, x + 46, cy], fill=color, width=width)
    c.line([x + 18, cy - 18, x, cy], fill=color, width=width)
    c.line([x, cy, x + 18, cy + 18], fill=color, width=width)


# --------------------------------------------------------------------------- #
# System status-bar widgets
# --------------------------------------------------------------------------- #
def signal_bars(c, x, cy, color, bars=4, slot=11, max_h=30):
    for i in range(bars):
        h = max(6, int(max_h * (i + 1) / bars))
        x0 = x + i * (slot + 6)
        c.rect([x0, cy + max_h // 2 - h // 2, x0 + slot, cy + max_h // 2 + h // 2],
               fill=color)


def wifi_arcs(c, cx, cy, color, rings=3):
    """Nested arcs opening upward, anchored on a small dot."""
    dot_r = 5
    c.ellipse([cx - dot_r, cy + 22 - dot_r, cx + dot_r, cy + 22 + dot_r], fill=color)
    for i in range(rings):
        r = 11 + i * 11
        c.arc([cx - r, cy + 22 - r, cx + r, cy + 22 + r],
              start=215, end=325, fill=color, width=5)


def battery(c, x, cy, color, level=0.7):
    w, h = 54, 28
    x0, y0 = x, cy - h // 2
    c.rounded([x0, y0, x0 + w, y0 + h], radius=8, outline=color, width=4)
    c.rect([x0 + w + 3, y0 + 8, x0 + w + 9, y0 + h - 8], fill=color)
    c.rounded([x0 + 5, y0 + 5, x0 + 5 + int((w - 10) * level), y0 + h - 5],
              radius=5, fill=color)