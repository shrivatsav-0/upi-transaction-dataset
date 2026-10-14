"""Central configuration: app registry, status registry, palettes and knobs.

Everything tunable lives here so the renderers stay dumb.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, TypeVar

K = TypeVar("K")


def weighted_pick(rng: random.Random, table: Mapping[K, float]) -> K:
    """Pick a key from {key: weight}. Weights need not sum to 1.

    Draws exactly ONE uniform sample and walks the cumulative thresholds. Calling
    rng.random() inside the loop instead would give every later key a fresh
    chance and badly skew the distribution.
    """
    total = sum(table.values())
    target = rng.random() * total
    upto = 0.0
    for key, weight in table.items():
        upto += weight
        if target < upto:
            return key
    return next(reversed(table))


# --------------------------------------------------------------------------- #
# Apps
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AppSpec:
    key: str
    name: str
    accent: tuple           # top bar / brand colour, light theme
    accent_dark: tuple      # top bar / brand colour, dark theme
    layout: str             # which renderer in layouts/ to use
    international: bool = False   # PayPal-style, not UPI


APPS: dict[str, AppSpec] = {
    "gpay": AppSpec("gpay", "Google Pay", (26, 115, 232), (32, 34, 38), "gpay"),
    "phonepe": AppSpec("phonepe", "PhonePe", (93, 46, 140), (71, 34, 113), "phonepe"),
    "paytm": AppSpec("paytm", "Paytm", (0, 170, 220), (0, 132, 175), "paytm"),
    "cred": AppSpec("cred", "Cred", (12, 12, 14), (0, 0, 0), "tabular"),
    "bhim": AppSpec("bhim", "BHIM", (240, 110, 40), (196, 84, 28), "tabular"),
    "bank": AppSpec("bank", "Bank UPI", (0, 128, 96), (0, 92, 70), "tabular"),
    "paypal": AppSpec("paypal", "PayPal", (10, 74, 138), (4, 46, 86), "paypal",
                      international=True),
}

APP_ORDER = ["gpay", "phonepe", "paytm", "cred", "bhim", "bank", "paypal"]

# --------------------------------------------------------------------------- #
# Statuses
# --------------------------------------------------------------------------- #
# `label` is the stable label written to labels.jsonl / labels.csv.
# `india` / `intl` are the surface wordings actually rendered on screen, so the
# same bucket reads the way each family of apps really words it. Placeholders:
#   {amount} -> formatted amount, {payee} -> payee display name
@dataclass(frozen=True)
class StatusSpec:
    key: str
    label: str
    india: tuple
    intl: tuple
    color_key: str
    glyph: str
    has_utr: bool
    amount_sign: str
    note_india: str | None
    note_intl: str | None
    shows_reason: bool = False


SUCCESS = "success"
PENDING = "pending"
FAILED = "failed"
REVERSED = "reversed"

STATUSES: dict[str, StatusSpec] = {
    SUCCESS: StatusSpec(
        SUCCESS, "Payment Successful",
        india=("Payment Successful", "Paid successfully", "Transfer successful",
               "Payment completed", "Money sent to {payee}",
               "Payment of {amount} completed"),
        intl=("Completed", "Payment completed", "Transaction complete",
              "You sent {amount}", "Money sent"),
        color_key="ok", glyph="tick", has_utr=True, amount_sign="",
        note_india=None, note_intl=None,
    ),
    PENDING: StatusSpec(
        PENDING, "Payment Pending",
        india=("Payment processing", "Awaiting bank confirmation", "Payment pending",
               "Payment in progress", "Confirming with bank"),
        intl=("Pending", "Payment pending", "Awaiting confirmation",
              "Processing payment"),
        color_key="pending", glyph="clock", has_utr=True, amount_sign="",
        note_india="Amount debited, will be credited within 24 hours",
        note_intl="Waiting for the merchant to confirm",
    ),
    FAILED: StatusSpec(
        FAILED, "Payment Failed",
        india=("Payment failed", "Bank server issue", "Declined by bank",
               "Payment could not be completed", "Transaction failed"),
        intl=("Failed", "Payment failed", "Declined", "Payment unsuccessful"),
        color_key="fail", glyph="cross", has_utr=False, amount_sign="",
        note_india="No money was deducted from your account",
        note_intl="Your account was not charged",
        shows_reason=True,
    ),
    REVERSED: StatusSpec(
        REVERSED, "Payment Reversed",
        india=("Payment reversed", "Refund processed", "Amount refunded",
               "Money returned to your account", "Reversed to bank"),
        intl=("Refunded", "Payment refunded", "Money returned", "Reversed"),
        color_key="info", glyph="undo", has_utr=True, amount_sign="-",
        note_india="Amount credited back to your account",
        note_intl="Amount credited back to your account",
    ),
}

STATUS_ORDER = [SUCCESS, PENDING, FAILED, REVERSED]

# --------------------------------------------------------------------------- #
# Palettes
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Palette:
    name: str
    bg: tuple
    card: tuple
    card_alt: tuple
    text: tuple
    muted: tuple
    divider: tuple
    ok: tuple
    fail: tuple
    pending: tuple
    info: tuple
    on_accent: tuple
    border: tuple


PALETTES: dict[str, Palette] = {
    "light": Palette(
        name="light",
        bg=(245, 246, 248), card=(255, 255, 255), card_alt=(243, 244, 247),
        text=(28, 30, 34), muted=(120, 124, 132), divider=(228, 230, 234),
        ok=(30, 160, 90), fail=(211, 47, 47), pending=(214, 137, 16),
        info=(33, 118, 214), on_accent=(255, 255, 255), border=(206, 210, 218),
    ),
    "dark": Palette(
        name="dark",
        bg=(16, 16, 18), card=(30, 31, 36), card_alt=(40, 41, 47),
        text=(238, 239, 243), muted=(150, 152, 160), divider=(54, 56, 63),
        ok=(65, 200, 120), fail=(255, 82, 82), pending=(255, 179, 0),
        info=(100, 181, 246), on_accent=(255, 255, 255), border=(64, 66, 74),
    ),
}

# --------------------------------------------------------------------------- #
# Currencies  (PayPal)
# --------------------------------------------------------------------------- #
CURRENCIES = [
    ("USD", "$", 2),
    ("EUR", "€", 2),
    ("GBP", "£", 2),
]

# --------------------------------------------------------------------------- #
# Generation knobs
# --------------------------------------------------------------------------- #
@dataclass
class Settings:
    num_images: int = 600
    seed: int = 42

    # mix of axes -- values are relative weights
    app_weights: dict[str, float] = None
    status_weights: dict[str, float] = None
    theme_weights: dict[str, float] = None
    frame_weights: dict[str, float] = None          # full screenshot | cropped card
    vpa_weights: dict[str, float] = None             # masking variants

    themes: tuple = ("light", "dark")
    frames: tuple = ("full", "cropped")

    augment_ratio: float = 0.6
    jpeg_quality: tuple = (55, 92)
    img_size: tuple = (1080, 2000)

    out_dir: str = "dataset"

    def __post_init__(self):
        if self.app_weights is None:
            self.app_weights = {"gpay": 22, "phonepe": 22, "paytm": 18, "cred": 10,
                                "bhim": 8, "bank": 12, "paypal": 8}
        if self.status_weights is None:
            self.status_weights = {SUCCESS: 44, PENDING: 20, FAILED: 22, REVERSED: 14}
        if self.theme_weights is None:
            self.theme_weights = {"light": 50, "dark": 50}
        if self.frame_weights is None:
            self.frame_weights = {"full": 65, "cropped": 35}
        if self.vpa_weights is None:
            self.vpa_weights = {
                "plain": 32,          # fully visible
                "stars_mid": 22,      # 78925***32@okhdfc
                "stars_lead": 14,     # s*****@okaxis
                "x_mid": 12,          # 98765XXXX0@paytm
                "name_only": 12,      # no VPA at all, account tail instead
                "truncated": 8,       # name + VPA cut with an ellipsis
            }