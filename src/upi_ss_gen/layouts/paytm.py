"""Paytm: blue banner with inline sentence text, and the UPI Ref No pushed
down into a separate strip below the main card."""

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

    # ---- blue banner carrying the inline sentence
    y = top + bar_h
    banner_h = 210
    c.rect([0, y, c.w, y + banner_h], fill=accent)

    c.text((c.w // 2, y + 74), txn.amount_inline, 40, on_accent, "amount_inline",
           bold=True, anchor="mm")

    cx, cy, r = c.w - 132, y + 74, 36
    c.ellipse([cx - r, cy - r, cx + r, cy + r], fill=on_accent)
    icons.draw_status_glyph(c, spec.glyph, cx, cy, r, accent)

    c.text((c.w // 2, y + 148), txn.status_text, 32, on_accent, "status",
           bold=True, anchor="mm")

    y += banner_h + 56

    # ---- main card, without the reference numbers
    rows = [r for r in kv_rows(txn) if r[2] not in ("transaction_id", "utr")]
    y = _card(c, pal, y, rows, color=color)

    # ---- UPI Ref No strip, placed lower down
    strip_h = 150
    c.rounded([48, y, c.w - 48, y + strip_h], radius=28, fill=pal.card_alt)
    c.text((88, y + 44), "UPI Ref No", 30, pal.muted, "utr_label")
    c.text((88, y + 86), txn.utr if txn.has_utr else "Not available", 38,
           pal.text, "utr", bold=True)

    y += strip_h + 40

    # ---- app transaction ID row
    c.text((88, y), txn.txn_id_label, 28, pal.muted, "transaction_id_label")
    c.text((c.w - 88, y + 46), txn.txn_id, 32, pal.text, "transaction_id",
           bold=True, anchor="ra")

    draw_footer(c, pal, frame)


def _card(c, pal, top, rows, *, color):
    row_h = 108
    left, right = 48, c.w - 48
    c.rounded([left, top, right, top + 88 + row_h * len(rows)], radius=32, fill=pal.card)

    y = top + 60
    for i, (label, value, key) in enumerate(rows):
        c.text((left + 48, y), label, 30, pal.muted, f"{key}_label")
        if key == "status_reason":
            c.text((right - 48, y + 42), value, 32, color, key, bold=True, anchor="ra")
        else:
            c.text((right - 48, y + 42), value, 36, pal.text, key, bold=True,
                   anchor="ra")
        y += row_h
        if i < len(rows) - 1:
            c.hairline(y - 20, left + 48, right - 48, pal.divider)

    return top + 88 + row_h * len(rows)