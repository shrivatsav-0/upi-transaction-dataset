"""Synthetic data generation. Everything here is fake by construction."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from . import config, formats

FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh",
         "Krishna", "Ishaan", "Rohan", "Ananya", "Diya", "Saanvi", "Aadhya",
         "Pari", "Myra", "Riya", "Priya", "Neha", "Kavya", "Rahul", "Amit",
         "Sneha", "Pooja", "Karan", "Divya", "Manish", "Sanjay", "Deepak",
         "Sharan", "Shrivatsav", "Aniket", "Ved", "Tanvi", "Isha", "Rehan"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Reddy", "Nair", "Patel",
        "Mehta", "Jain", "Iyer", "Das", "Bose", "Rao", "Shetty", "Pillai",
        "Chatterjee", "Agarwal", "Malhotra", "Kapoor", "Joshi", "Yadav",
        "Shrivatsav", "Desai", "Menon"]

BANKS = ["HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank",
         "Kotak Mahindra Bank", "Punjab National Bank", "Bank of Baroda",
         "Canara Bank", "Union Bank of India", "IDFC FIRST Bank"]

MERCHANTS = ["Reliance Fresh", "More Supermarket", "Cafe Coffee Day",
             "Local Kirana Store", "Big Bazaar", "Zomato", "Swiggy",
             "BookMyShow", "Apollo Pharmacy", "Shell Petrol Pump",
             "City Hospital", "Urban Company", None, None]

FAILURE_REASONS = [
    "Insufficient balance in account",
    "Bank server did not respond",
    "Request timed out. Please try again",
    "Payment declined by bank",
    "Wrong MPIN entered",
    "UPI ID does not exist",
    "Transaction limit exceeded",
    "Internet connectivity lost",
    "Payment cancelled by customer",
    "Beneficiary bank unreachable",
    "Txn ID already used. Contact your bank",
]

PAYPAL_HANDLES = ["@sharan_s", "@venkatesh88", "@amrit.echo", "@paypal_support",
                  "@nikhil.m", "@zoya.k", "@dev.rao"]
PAYPAL_EMAILS = ["sharan.s@example.in", "amrit.echo@example.in",
                 "nikhil.m@example.in", "zoya.k@example.in", "dev.rao@example.in"]

_ALNUM = string.ascii_uppercase + string.digits


def _digits(rng, n):
    return "".join(rng.choices(string.digits, k=n))


def _alnum(rng, n):
    return "".join(rng.choices(_ALNUM, k=n))


def rand_name(rng) -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def rand_handle(rng) -> str:
    """A UPI handle. Sometimes dotted, sometimes numeric-prefixed."""
    style = rng.random()
    if style < 0.35:
        first = rng.choice(FIRST).lower()
        return f"{first}.{rng.choice(LAST).lower()[:3]}{rng.randint(1, 999)}"
    if style < 0.6:
        return f"{rng.choice(FIRST).lower()}{rng.randint(1, 9999)}"
    return _digits(rng, rng.randint(8, 10))


def rand_vpa(rng) -> str:
    return f"{rand_handle(rng)}@{rng.choice(formats.VPA_HANDLES)}"


def rand_acct_tail(rng, digits=4) -> str:
    return _digits(rng, digits)


def rand_utr(rng) -> str:
    return _digits(rng, 12)


def rand_phone(rng) -> str:
    return "+91 " + rng.choice("6789") + _digits(rng, 4) + " " + _digits(rng, 5)


def rand_txn_id(rng, app_key: str) -> str:
    """Each family of apps uses its own reference-number shape."""
    if app_key == "gpay":
        return _alnum(rng, 22)
    if app_key == "phonepe":
        return "T" + _digits(rng, 20)
    if app_key == "paytm":
        return _digits(rng, 16)
    if app_key == "paypal":
        return _alnum(rng, 17)          # PayPal transaction id
    return _alnum(rng, 18)


def rand_datetime(rng):
    base = datetime(2026, 1, 1) + timedelta(days=rng.randint(0, 300),
                                           seconds=rng.randint(0, 86399))
    return base


def rand_clock(rng) -> str:
    """Short 24h clock for the Android status bar, e.g. '16:12'."""
    return f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"


# --------------------------------------------------------------------------- #
# Transaction record
# --------------------------------------------------------------------------- #
@dataclass
class Transaction:
    """Everything a renderer needs, plus everything that goes into labels."""

    # classification
    app_key: str
    app_name: str
    theme: str
    frame: str
    status: str                 # canonical bucket key
    status_label: str           # stable label for the dataset
    status_text: str            # what is actually rendered on screen

    # money
    amount: float
    amount_display: str         # e.g. "₹1,500.50" / "-₹1,500.50"
    amount_inline: str          # e.g. "Paid ₹1,500.50 to Zomato"
    currency: str               # "INR" for UPI apps
    currency_symbol: str

    # when
    datetime_text: str
    date_only: str

    # who
    payee_name: str
    payee_name_display: str    # possibly truncated
    payee_vpa: str              # possibly masked, "" when not shown
    vpa_visible: bool
    vpa_style: str
    payee_handle: str           # PayPal
    payer_name: str
    payer_bank: str
    account_tail: str

    # references
    utr: str
    has_utr: bool
    txn_id: str
    txn_id_label: str
    status_reason: str

    def as_fields(self) -> dict:
        return asdict(self)


def make_transaction(rng: random.Random, settings: config.Settings) -> Transaction:
    app_key = config.weighted_pick(rng, settings.app_weights)
    app = config.APPS[app_key]
    theme = config.weighted_pick(rng, settings.theme_weights)
    frame = config.weighted_pick(rng, settings.frame_weights)

    status_key = config.weighted_pick(rng, settings.status_weights)
    spec = config.STATUSES[status_key]

    # ---- money
    currency, symbol = ("INR", "\u20b9")
    if app.international:
        currency, symbol, _ = rng.choice(config.CURRENCIES)
    amount = formats.pick_amount_value(rng)
    pool = (formats.REFUND_INLINE_TEMPLATES if spec.amount_sign == "-"
            else formats.INLINE_TEMPLATES)
    inline_tpl = rng.choice(pool)

    # render the magnitude, then prefix the sign as a string -- folding a "-"
    # into the float would corrupt the comma grouping in the formatters
    if app.international:
        amount_display = spec.amount_sign + formats.render_foreign(
            amount, symbol, currency, rng)
    else:
        amount_display = spec.amount_sign + formats.pick_amount_style(rng).render(
            amount, symbol=symbol)

    # ---- who
    payee_name = rand_name(rng)
    merchant = rng.choice(MERCHANTS)
    if merchant:
        payee_name = merchant

    payer_name = rand_name(rng)
    payer_bank = rng.choice(BANKS)
    acct_tail = rand_acct_tail(rng)

    # ---- recipient masking (UPI apps only; PayPal shows handles/emails)
    vpa_style = "n/a"
    payee_handle = ""
    if app.international:
        payee_handle = rng.choice(PAYPAL_HANDLES if rng.random() < 0.6 else PAYPAL_EMAILS)
        payee_name = payee_handle.lstrip("@")
        vpa_visible = True
        payee_vpa = payee_handle
    else:
        vpa_style = config.weighted_pick(rng, settings.vpa_weights)
        raw_vpa = rand_vpa(rng)
        vpa_visible = True
        payee_vpa = raw_vpa

        if vpa_style == "plain":
            pass
        elif vpa_style in ("stars_mid", "stars_lead", "x_mid"):
            payee_vpa = formats.mask_vpa(rng, raw_vpa, vpa_style)
        elif vpa_style == "name_only":
            # No @bank handle at all -- app only shows the name + account tail
            payee_vpa = ""
            vpa_visible = False
        elif vpa_style == "truncated":
            payee_vpa = raw_vpa
            if len(payee_vpa) > 22:
                payee_vpa = payee_vpa[:22] + "..."

    payee_name_display = formats.truncate_name(payee_name, rng.choice([14, 16, 18, 22]))

    # ---- when
    when = rand_datetime(rng)
    datetime_text = formats.fmt_date_time(when, rng)
    date_only = when.strftime("%d %b %Y")

    amount_inline = inline_tpl.format(amount=amount_display, payee=payee_name_display)

    # ---- status surface text
    variants = spec.intl if app.international else spec.india
    status_text = rng.choice(variants).format(amount=amount_display,
                                             payee=payee_name_display)

    reason = ""
    if spec.shows_reason:
        reason = rng.choice(FAILURE_REASONS)

    return Transaction(
        app_key=app_key,
        app_name=app.name,
        theme=theme,
        frame=frame,
        status=status_key,
        status_label=spec.label,
        status_text=status_text,
        amount=amount,
        amount_display=amount_display,
        amount_inline=amount_inline,
        currency=currency,
        currency_symbol=symbol,
        datetime_text=datetime_text,
        date_only=date_only,
        payee_name=payee_name,
        payee_name_display=payee_name_display,
        payee_vpa=payee_vpa,
        vpa_visible=vpa_visible,
        vpa_style=vpa_style,
        payee_handle=payee_handle,
        payer_name=payer_name,
        payer_bank=payer_bank,
        account_tail="XXXX" + acct_tail,
        utr=rand_utr(rng) if spec.has_utr else "",
        # PayPal does not issue UTRs, so the flag is false there regardless of
        # the status bucket.
        has_utr=spec.has_utr and not app.international,
        txn_id=rand_txn_id(rng, app_key),
        txn_id_label=f"{app.name} transaction ID",
        status_reason=reason,
    )