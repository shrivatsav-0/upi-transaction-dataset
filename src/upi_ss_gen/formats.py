"""Display formatting: amounts, dates/times, and VPA masking.

All string builders here are platform-safe: `strftime` directives like `%-I`
do not work on Windows, so every format is assembled by hand.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

MONTHS_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# --------------------------------------------------------------------------- #
# Amounts
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AmountStyle:
    """How to render a numeric amount."""
    prefix: str        # "₹", "₹ ", "INR ", "Rs. "
    grouping: str      # "none" | "intl" | "indian"
    decimals: int      # 0 | 2

    def render(self, value: float, symbol: str = "\u20b9") -> str:
        prefix = self.prefix.replace("\u20b9", symbol)
        return prefix + _format_number(value, self.grouping, self.decimals)


def _format_number(value: float, grouping: str, decimals: int) -> str:
    qty = f"{value:.{decimals}f}"
    if "." in qty:
        whole, frac = qty.split(".")
    else:
        whole, frac = qty, None

    if grouping == "none":
        body = whole
    elif grouping == "indian":
        body = _group_indian(whole)
    else:
        body = _group_intl(whole)

    return f"{body}.{frac}" if frac else body


def _group_intl(digits: str) -> str:
    out = []
    for i, ch in enumerate(reversed(digits)):
        if i and i % 3 == 0:
            out.append(",")
        out.append(ch)
    return "".join(reversed(out))


def _group_indian(digits: str) -> str:
    """Indian lakh/crore grouping: 1234567 -> 12,34,567."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    parts.append(head)
    return ",".join(reversed(parts)) + "," + tail


# Weighted so the common "₹1,500.50" and "₹1500" forms dominate.
AMOUNT_STYLES = [
    (AmountStyle("\u20b9", "intl", 2), 22),
    (AmountStyle("\u20b9", "none", 0), 18),
    (AmountStyle("\u20b9", "indian", 2), 16),
    (AmountStyle("\u20b9 ", "intl", 0), 12),
    (AmountStyle("\u20b9 ", "none", 0), 10),
    (AmountStyle("INR ", "intl", 0), 8),
    (AmountStyle("Rs. ", "none", 0), 8),
    (AmountStyle("\u20b9", "indian", 0), 6),
]

# Inline phrasings used by Paytm-style banners.
INLINE_TEMPLATES = [
    "Paid {amount} to {payee}",
    "You sent {amount} to {payee}",
    "Paid {amount}",
    "{amount} paid successfully to {payee}",
]

# A refund carries a negative amount, so "You sent -Rs. 974" reads as nonsense.
# Reversed/refunded receipts get their own phrasings instead.
REFUND_INLINE_TEMPLATES = [
    "Refund of {amount} to {payee}",
    "{amount} returned to {payee}",
    "Refunded {amount} to {payee}",
    "{amount} reversed to {payee}",
]


def render_foreign(value: float, symbol: str, code: str, rng: random.Random) -> str:
    """PayPal amounts.

    Always intl grouping and cents -- Indian lakh grouping never applies to a
    foreign currency, and the rupee-prefixed styles below do not apply either.
    """
    body = _format_number(abs(value), "intl", 2)
    if rng.random() < 0.35:
        return f"{code} {body}"
    return f"{symbol}{' ' if rng.random() < 0.4 else ''}{body}"


def pick_amount_style(rng: random.Random) -> AmountStyle:
    """One uniform draw walked against cumulative weights (see config.weighted_pick)."""
    total = sum(w for _, w in AMOUNT_STYLES)
    target = rng.random() * total
    upto = 0.0
    for style, weight in AMOUNT_STYLES:
        upto += weight
        if target < upto:
            return style
    return AMOUNT_STYLES[0][0]


def pick_amount_value(rng: random.Random) -> float:
    r = rng.random()
    if r < 0.45:
        amt = rng.randint(10, 999)
    elif r < 0.82:
        amt = rng.randint(1000, 9999)
    elif r < 0.96:
        amt = rng.randint(10000, 99999)
    else:
        amt = rng.randint(100000, 999999)
    return float(amt)


# --------------------------------------------------------------------------- #
# Dates / times
# --------------------------------------------------------------------------- #
def _h12(dt) -> int:
    return dt.hour % 12 or 12


def _ampm(dt) -> str:
    return "AM" if dt.hour < 12 else "PM"


def fmt_date_time(dt, rng: random.Random) -> str:
    """One of the four real-world UPI timestamp shapes."""
    d, m, y = dt.day, dt.month, dt.year
    mon = MONTHS_ABBR[m - 1]
    h24 = dt.hour
    h12 = _h12(dt)
    mi, se = dt.minute, dt.second
    ap = _ampm(dt)
    ap_lower = ap.lower()

    choice = rng.randrange(4)
    if choice == 0:
        return f"{d:02d} {mon} {y}, {h12}:{mi:02d} {ap_lower}"
    if choice == 1:
        return f"{d:02d}/{m:02d}/{y} at {h24:02d}:{mi:02d}:{se:02d}"
    if choice == 2:
        return f"{mon} {d}, {y} {h24:02d}:{mi:02d} {ap} IST"
    return f"{d:02d}-{m:02d}-{y}, {h24:02d}:{mi:02d}"


# --------------------------------------------------------------------------- #
# VPA masking
# --------------------------------------------------------------------------- #
VPA_HANDLES = ["okhdfcbank", "oksbi", "okicici", "okaxis", "okkotak", "ybl", "ibl",
               "axl", "paytm", "apl", "upi", "pingpay", "paypal"]


def mask_handle(rng: random.Random, handle: str, style: str) -> str:
    """Mask part of a VPA handle. Bank suffix is always left visible.

    Produces the shapes seen in real apps:
        78925***32@okhdfc    stars_mid
        s*****@okaxis        stars_lead
        98765XXXX0@paytm     x_mid
    """
    n = len(handle)
    if style == "stars_mid":
        keep_head = min(6, max(3, n // 2))
        keep_tail = 2 if n - keep_head > 2 else 0
        hidden = n - keep_head - keep_tail
        return handle[:keep_head] + "*" * hidden + handle[keep_head + hidden:]

    if style == "stars_lead":
        keep_head = 1
        return handle[:keep_head] + "*" * (n - keep_head)

    if style == "x_mid":
        keep_head = min(5, max(1, n - 3))
        hidden = n - keep_head - 2
        return handle[:keep_head] + "X" * hidden + handle[keep_head + hidden:]

    return handle  # plain


def mask_vpa(rng: random.Random, vpa: str, style: str) -> str:
    """Apply a masking style to a full `handle@bank` VPA string.

    The bank suffix is always left intact -- that is what real apps do, since
    it is the only part the payer needs to verify.
    """
    handle, _, bank = vpa.partition("@")
    if style == "plain":
        return vpa
    return f"{mask_handle(rng, handle, style)}@{bank}"


def truncate_name(name: str, max_len: int = 16) -> str:
    """Shorten a long name the way narrow screens do: 'Sharan Shrivats...'"""
    if len(name) <= max_len:
        return name
    return name[:max_len].rstrip() + "..."