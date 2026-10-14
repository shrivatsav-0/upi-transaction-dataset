"""Google Pay: giant hero amount in the upper third, round avatar, and a
'Transaction details' accordion that is sometimes collapsed."""

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

    # ---- round avatar carrying the status colour
    cy = top + bar_h + 144
    icons.avatar(c, c.w // 2, cy, 84, color, on_accent)

    y = cy + 132
    c.text((c.w // 2, y), txn.status_text, 44, color, "status", bold=True, anchor="mm")

    # ---- giant hero amount
    y += 96
    c.text((c.w // 2, y), txn.amount_display, 104, pal.text, "amount",
           bold=True, anchor="mm")

    # 'to' and the name are drawn as two runs so the payee_name bbox covers
    # exactly the name, not the prefix. Measuring a lone " " returns zero
    # advance in PIL, so take the space width as the difference of "x x" and "xx".
    y += 78
    w_to = c.width_of("to", 34)
    w_name = c.width_of(txn.payee_name_display, 34)
    gap = c.width_of("x x", 34) - c.width_of("xx", 34)
    x0 = c.w // 2 - (w_to + gap + w_name) // 2
    c.text((x0, y), "to", 34, pal.muted, "payee_prefix")
    c.text((x0 + w_to + gap, y), txn.payee_name_display, 34, pal.muted, "payee_name")

    note = spec.note_india
    if note:
        y += 52
        c.text((c.w // 2, y), note, 27, pal.muted, "status_note", anchor="mm")

    y += 90
    _accordion(c, pal, y, txn, expanded=rng.random() < 0.65)

    draw_footer(c, pal, frame)


def _accordion(c, pal, top, txn, *, expanded):
    """Header row with a chevron; the body is only drawn when expanded."""
    left, right = 60, c.w - 60
    header_h = 108
    row_h = 112
    rows = kv_rows(txn)
    body_h = (20 + row_h * len(rows)) if expanded else 0
    height = header_h + body_h

    c.rounded([left, top, right, top + height], radius=32, fill=pal.card)

    head_mid = top + header_h // 2
    c.text((left + 48, head_mid), "Transaction details", 36, pal.text,
           "accordion_header", bold=True, anchor="lm")
    icons.chevron(c, right - 70, head_mid, 30, pal.muted, width=7,
                  direction="down" if expanded else "right")

    if not expanded:
        # collapsed: the header itself is the only ground truth on screen
        return

    y = top + header_h + 20
    for i, (label, value, key) in enumerate(rows):
        c.text((left + 48, y), label, 28, pal.muted, f"{key}_label")
        c.text((right - 48, y + 40), value, 34, pal.text, key, bold=True, anchor="ra")
        y += row_h
        if i < len(rows) - 1:
            c.hairline(y - 20, left + 48, right - 48, pal.divider)