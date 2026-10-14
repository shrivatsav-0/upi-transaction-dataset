"""PayPal: international receipts.

Different vocabulary ('You sent...', 'Completed', 'Refunded'), multi-currency
amounts, a 17-character alphanumeric transaction id, and a recipient that is a
@handle or an email address rather than a UPI VPA.
"""

from __future__ import annotations

from .. import config, icons
from .base import draw_footer, kv_rows, palette_for, status_text


def render(c, app, theme, txn, frame, rng):
    pal = palette_for(app, theme)
    color = status_text(pal, txn)
    spec = config.STATUSES[txn.status]
    on_accent = pal.on_accent

    top = frame.top
    bar_h = 140
    c.rect([0, top, c.w, top + bar_h], fill=app.accent_dark if theme == "dark"
           else app.accent)
    c.text((c.w // 2, top + bar_h // 2), app.name, 40, on_accent, "app",
           bold=True, anchor="mm")

    # ---- 'You sent <amount> to <handle>', with the amount in its own box
    y = top + bar_h + 70
    c.text((c.w // 2, y), "You sent", 34, pal.muted, "pp_heading", anchor="mm")

    y += 84
    c.text((c.w // 2, y), txn.amount_display, 76, pal.text, "amount",
           bold=True, anchor="mm")

    y += 70
    c.text((c.w // 2, y), "to", 32, pal.muted, "pp_to", anchor="mm")

    y += 66
    c.text((c.w // 2, y), txn.payee_handle, 44, pal.text, "payee_handle",
           bold=True, anchor="mm")

    y += 132
    cx, cy, r = c.w // 2, y, 70
    c.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    icons.draw_status_glyph(c, spec.glyph, cx, cy, r, on_accent)

    y += 116
    c.text((c.w // 2, y), txn.status_text, 44, color, "status", bold=True, anchor="mm")

    note = spec.note_intl
    if note:
        y += 56
        c.text((c.w // 2, y), note, 28, pal.muted, "status_note", anchor="mm")

    y += 92
    _detail_card(c, pal, y, txn, color=color)

    draw_footer(c, pal, frame, text=f"Currency: {txn.currency}")


def _detail_card(c, pal, top, txn, *, color):
    rows = kv_rows(txn)
    row_h = 104
    left, right = 48, c.w - 48
    c.rounded([left, top, right, top + 84 + row_h * len(rows)], radius=32,
              fill=pal.card)

    y = top + 56
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