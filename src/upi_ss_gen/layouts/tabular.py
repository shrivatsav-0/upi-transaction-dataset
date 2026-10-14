"""Tabular slip renderer used by Cred, BHIM and the generic bank app.

Minimalist, with a bordered grid of cells rather than loose key/value lines.
"""

from __future__ import annotations

from .. import config, icons
from .base import accent_for, draw_footer, kv_rows, palette_for, status_text


def render(c, app, theme, txn, frame, rng):
    pal = palette_for(app, theme)
    accent = accent_for(app, theme)
    color = status_text(pal, txn)
    spec = config.STATUSES[txn.status]

    top = frame.top
    bar_h = 140
    c.rect([0, top, c.w, top + bar_h], fill=accent)
    on_accent = pal.on_accent
    c.text((c.w // 2, top + bar_h // 2), app.name, 40, on_accent, "app",
           bold=True, anchor="mm")

    # ---- status strip
    y = top + bar_h + 56
    c.text((64, y), txn.status_text, 44, color, "status", bold=True)
    y += 66

    c.text((64, y), txn.amount_display, 78, pal.text, "amount", bold=True)
    y += 96

    if spec.note_india:
        c.text((64, y), spec.note_india, 28, pal.muted, "status_note")
        y += 48

    # 'to' and the name are separate runs so the payee_name bbox covers only the
    # name
    y_line = y
    w_to = c.width_of("to", 34)
    gap = c.width_of("x x", 34) - c.width_of("xx", 34)
    c.text((64, y_line), "to", 34, pal.muted, "payee_prefix")
    c.text((64 + w_to + gap, y_line), txn.payee_name_display, 34, pal.muted,
           "payee_name")
    y += 70

    _slip(c, pal, y, txn, color=color)

    draw_footer(c, pal, frame)


def _slip(c, pal, top, txn, *, color):
    """Bordered table: one bordered cell per field, header row on top."""
    rows = kv_rows(txn)
    cell_h = 104
    left, right = 48, c.w - 48
    header_h = 84
    height = header_h + cell_h * len(rows)

    c.rect([left, top, right, top + height], fill=pal.card,
           outline=pal.border, width=3)

    # header band
    c.rect([left, top, right, top + header_h], fill=pal.card_alt)
    c.line([left, top + header_h, right, top + header_h], fill=pal.border, width=3)
    c.text((left + 36, top + header_h // 2), "TRANSACTION DETAILS", 28, pal.muted,
           "slip_header", bold=True, anchor="lm")

    y = top + header_h
    for i, (label, value, key) in enumerate(rows):
        c.line([left, y, right, y], fill=pal.border, width=3)
        # label sits in a narrow left gutter, value fills the rest
        c.text((left + 36, y + cell_h // 2), label, 28, pal.muted,
               f"{key}_label", anchor="lm")
        fill = color if key == "status_reason" else pal.text
        c.text((right - 36, y + cell_h // 2), value, 34, fill, key,
               bold=True, anchor="rm")
        y += cell_h

    c.line([left, y, right, y], fill=pal.border, width=3)