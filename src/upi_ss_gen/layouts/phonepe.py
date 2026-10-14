"""PhonePe: purple card, two-column layout, with a separate
'PhonePe Transaction ID' (T...) and a 12-digit UTR."""

from __future__ import annotations

from .. import config, icons
from .base import accent_for, draw_footer, kv_rows, palette_for, status_text


def render(c, app, theme, txn, frame, rng):
    pal = palette_for(app, theme)
    accent = accent_for(app, theme)
    color = status_text(pal, txn)
    spec = config.STATUSES[txn.status]
    on_accent = pal.on_accent

    top = frame.top
    bar_h = 150
    c.rect([0, top, c.w, top + bar_h], fill=accent)
    icons.back_arrow(c, 46, top + bar_h // 2, on_accent, width=8)
    c.text((c.w // 2, top + bar_h // 2), app.name, 42, on_accent, "app",
           bold=True, anchor="mm")

    # ---- the signature purple card
    y = top + bar_h + 56
    card_h = 400
    c.rounded([48, y, c.w - 48, y + card_h], radius=40, fill=accent)

    c.text((c.w // 2, y + 74), txn.status_text, 40, on_accent, "status",
           bold=True, anchor="mm")

    c.text((c.w // 2, y + 166), txn.amount_display, 86, on_accent, "amount",
           bold=True, anchor="mm")

    c.text((c.w // 2, y + 236), f"to {txn.payee_name_display}", 32, on_accent,
           "payee_name", anchor="mm")

    # status glyph in the corner of the card
    cx, cy, r = c.w - 130, y + 74, 34
    c.ellipse([cx - r, cy - r, cx + r, cy + r], fill=on_accent)
    icons.draw_status_glyph(c, spec.glyph, cx, cy, r, accent)

    y += card_h + 64

    if spec.note_india:
        c.text((c.w // 2, y), spec.note_india, 28, pal.muted, "status_note",
               anchor="mm")
        y += 58

    _two_column(c, pal, y, txn)

    draw_footer(c, pal, frame)


def _two_column(c, pal, top, txn):
    """Two-column table: value on the left, label on the right."""
    rows = kv_rows(txn)
    row_h = 108
    left, right = 48, c.w - 48

    c.rounded([left, top, right, top + 88 + row_h * len(rows)], radius=32, fill=pal.card)

    y = top + 60
    for i, (label, value, key) in enumerate(rows):
        c.text((left + 48, y), value, 34, pal.text, key, bold=True)
        c.text((right - 48, y + 6), label, 28, pal.muted, f"{key}_label", anchor="ra")
        y += row_h
        if i < len(rows) - 1:
            c.hairline(y - 20, left + 48, right - 48, pal.divider)