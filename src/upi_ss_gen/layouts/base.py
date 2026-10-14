"""Shared helpers every app layout builds on."""

from __future__ import annotations

from .. import config, icons


def palette_for(app: config.AppSpec, theme: str) -> config.Palette:
    return config.PALETTES[theme]


def accent_for(app: config.AppSpec, theme: str) -> tuple:
    return app.accent_dark if theme == "dark" else app.accent


def status_color(app: config.AppSpec, theme: str, txn) -> tuple:
    pal = palette_for(app, theme)
    return getattr(pal, config.STATUSES[txn.status].color_key)


def draw_app_bar(c, app: config.AppSpec, theme: str, top: int, subtitle: str = None):
    """Accent bar carrying the app name. Returns the y below it."""
    pal = palette_for(app, theme)
    accent = accent_for(app, theme)
    h = 150
    c.rect([0, top, c.w, top + h], fill=accent)
    on_accent = pal.on_accent

    mid = top + h // 2
    c.text((c.w // 2, mid), app.name, 46, on_accent, "app", bold=True, anchor="mm")

    if subtitle:
        c.text((c.w // 2, mid + 44), subtitle, 26, on_accent, "app_subtitle",
               anchor="mm")
    return top + h


def status_text(pal: config.Palette, txn) -> tuple:
    return getattr(pal, config.STATUSES[txn.status].color_key)


def kv_rows(txn) -> list[tuple[str, str, str]]:
    """The canonical label/value/field-key rows.

    Which rows survive depends on the app family and on how the app masks the
    recipient: a `name_only` receipt has no VPA at all, and PayPal shows a
    handle plus a currency rather than a UPI ID or a UTR.
    """
    international = txn.app_key == "paypal"

    if international:
        rows = [("To", txn.payee_handle, "payee_handle")]
    else:
        rows = [("Paid to", txn.payee_name_display, "payee_name")]
        if txn.vpa_visible:
            rows.append(("UPI ID", txn.payee_vpa, "payee_vpa"))
        else:
            rows.append(("Account", f"A/c {txn.account_tail}", "account_tail"))
        rows.append(("From", txn.payer_name, "payer_name"))
        rows.append(("Bank", f"{txn.payer_bank} {txn.account_tail}", "payer_bank"))

    rows.append(("Date", txn.datetime_text, "datetime"))

    if txn.status_reason:
        rows.append(("Reason", txn.status_reason, "status_reason"))

    rows.append((txn.txn_id_label, txn.txn_id, "transaction_id"))

    if international:
        rows.append(("Currency", txn.currency, "currency"))
    elif txn.has_utr:
        rows.append(("UPI transaction ID", txn.utr, "utr"))

    return rows


def draw_kv_card(c, app, theme, txn, top, *, pad=60, row_h=112, label_size=32,
                 value_size=38, radius=32, card_fill=None):
    """Two-column label/value card. Returns the y below the card."""
    pal = palette_for(app, theme)
    rows = kv_rows(txn)
    fill = card_fill or pal.card

    height = 100 + row_h * len(rows)
    left, right = pad, c.w - pad

    c.rounded([left, top, right, top + height], radius=radius, fill=fill)

    y = top + 64
    for i, (label, value, key) in enumerate(rows):
        c.text((left + 48, y), label, label_size, pal.muted, f"{key}_label")
        if key == "status_reason":
            c.text((right - 48, y + 40), value, label_size + 2,
                   status_text(pal, txn), key, bold=True, anchor="ra")
        else:
            c.text((right - 48, y + 40), value, value_size, pal.text, key,
                   bold=True, anchor="ra")
        y += row_h
        if i < len(rows) - 1:
            c.hairline(y - 20, left + 48, right - 48, pal.divider)

    return top + height


def draw_footer(c, pal, frame, text="Powered by UPI"):
    """Footer sits above the nav bar on full screenshots, flush on cropped ones."""
    y = c.h - frame.bottom - 50
    c.text((c.w // 2, y), text, 30, pal.muted, "footer", anchor="mm")