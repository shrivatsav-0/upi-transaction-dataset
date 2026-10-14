#!/usr/bin/env python3
"""
Synthetic UPI receipt generator for OCR training.

Generates receipt-style screenshots for Google Pay, PhonePe, Paytm, BHIM and a
generic bank app, in light & dark themes, across MULTIPLE transaction states
(successful / failed / pending / refunded / processing), with optional
augmentations. For every image it emits ground-truth labels: field values AND
bounding boxes.

NOTE: All data is randomly generated and fake. No real people, VPAs, phone
numbers or transactions are used. This exists so you can train OCR without
scraping real screenshots (which carry PII and have no labels).

Requirements:
    pip install pillow

Run:
    python upi_receipt_generator.py

Output (next to this script, in ./dataset):
    dataset/images/<app>_<status>_<theme>_<id>.jpg   the receipt image
    dataset/annotations/<same>.json                 per-image fields + bboxes
    dataset/labels.jsonl                            one JSON object per line (all images)
    dataset/labels.csv                              flat field table (all images)
    dataset/summary.json                            counts per app / status / theme
"""

import csv
import json
import os
import random
import string
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --------------------------------------------------------------------------- #
# Config  --  tweak these
# --------------------------------------------------------------------------- #
NUM_IMAGES      = 600
APPS            = ["gpay", "phonepe", "paytm", "bhim", "bank"]
THEMES          = ["light", "dark"]

# (status label, relative weight)  --  weights need not sum to anything
STATUSES        = [
    ("Payment Successful", 46),
    ("Payment Failed",     20),
    ("Pending",           14),
    ("Processing",        10),
    ("Refunded",          10),
]

AUGMENT_RATIO   = 0.6          # fraction of images that get degraded
JPEG_QUALITY    = (55, 92)     # random save quality range
OUT_DIR         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
IMG_SIZE        = (1080, 2000) # portrait phone screenshot
SEED            = 42

random.seed(SEED)

# --------------------------------------------------------------------------- #
# Fonts  --  tries Windows system fonts, falls back to PIL default
# --------------------------------------------------------------------------- #
_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeui.ttf",     # has the ₹ glyph
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _find_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_REG_PATH = _find_font(_FONT_CANDIDATES)
_BOLD_PATH = _find_font(_FONT_BOLD_CANDIDATES) or _REG_PATH


def font(size, bold=False):
    path = _BOLD_PATH if bold else _REG_PATH
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# --------------------------------------------------------------------------- #
# Fake-data generators
# --------------------------------------------------------------------------- #
FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh",
         "Krishna", "Ishaan", "Rohan", "Ananya", "Diya", "Saanvi", "Aadhya",
         "Pari", "Myra", "Riya", "Priya", "Neha", "Kavya", "Rahul", "Amit",
         "Sneha", "Pooja", "Karan", "Divya", "Manish", "Sanjay", "Deepak"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Kumar", "Reddy", "Nair", "Patel",
        "Mehta", "Jain", "Iyer", "Das", "Bose", "Rao", "Shetty", "Pillai",
        "Chatterjee", "Agarwal", "Malhotra", "Kapoor", "Joshi", "Yadav"]
BANKS = ["HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank",
         "Kotak Mahindra Bank", "Punjab National Bank", "Bank of Baroda",
         "Canara Bank", "Union Bank of India", "IDFC FIRST Bank"]
VPA_BANKS = ["okhdfcbank", "oksbi", "okicici", "okaxis", "ybl", "ibl", "axl",
             "paytm", "apl", "pingpay"]
MERCHANTS = ["Reliance Fresh", "More Supermarket", "Cafe Coffee Day",
             "Local Kirana Store", "Big Bazaar", "Zomato", "Swiggy",
             "BookMyShow", "Apollo Pharmacy", "Shell Petrol Pump", None, None]

# Reasons a UPI payment can fail / be stuck -- shown on failed & pending cards
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

# What each status looks like on screen.
#   color_key  -> palette entry used for the badge, headline and glyph
#   glyph      -> which icon to draw inside the circle
#   has_utr    -> whether a UTR / bank reference exists for this state
#   amount_sign-> "" for a normal charge, "-" for a credit-back (refund)
#   note       -> small helper line under the amount
STATUS_META = {
    "Payment Successful": {
        "color_key": "ok", "glyph": "tick", "has_utr": True,
        "amount_sign": "", "headline": "Payment Successful",
        "note": None,
    },
    "Payment Failed": {
        "color_key": "fail", "glyph": "cross", "has_utr": False,
        "amount_sign": "", "headline": "Payment Failed",
        "note": "No money was deducted from your account",
    },
    "Pending": {
        "color_key": "pending", "glyph": "clock", "has_utr": True,
        "amount_sign": "", "headline": "Payment Pending",
        "note": "Amount debited, will be credited within 24 hours",
    },
    "Processing": {
        "color_key": "info", "glyph": "spinner", "has_utr": True,
        "amount_sign": "", "headline": "Payment Processing",
        "note": "Payment initiated, waiting for confirmation",
    },
    "Refunded": {
        "color_key": "info", "glyph": "undo", "has_utr": True,
        "amount_sign": "-", "headline": "Payment Refunded",
        "note": "Amount credited back to your account",
    },
}


def pick_status():
    """Weighted random pick from STATUSES."""
    total = sum(w for _, w in STATUSES)
    r = random.uniform(0, total)
    upto = 0.0
    for label, weight in STATUSES:
        upto += weight
        if r <= upto:
            return label
    return STATUSES[0][0]


def status_slug(status):
    return status.lower().replace(" ", "_")


def rand_name():
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


def rand_vpa(name):
    handle = name.split()[0].lower() + str(random.randint(1, 9999))
    return f"{handle}@{random.choice(VPA_BANKS)}"


def rand_phone():
    return "+91 " + random.choice("6789") + "".join(random.choices("0123456789", k=4)) \
           + " " + "".join(random.choices("0123456789", k=5))


def rand_amount():
    choice = random.random()
    if choice < 0.5:
        amt = random.randint(10, 999)
    elif choice < 0.85:
        amt = random.randint(1000, 9999)
    else:
        amt = random.randint(10000, 100000)
    if random.random() < 0.3:
        return f"{amt}.{random.randint(0,99):02d}"
    return f"{amt}"


def rand_utr():
    return "".join(random.choices(string.digits, k=12))


def rand_txn_id(app):
    if app == "gpay":
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=22))
    if app == "phonepe":
        return "T" + "".join(random.choices(string.digits, k=20))
    if app == "paytm":
        return "".join(random.choices(string.digits, k=16))
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=18))


def rand_datetime():
    base = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 300),
                                             seconds=random.randint(0, 86399))
    return base.strftime("%d %b %Y, %I:%M %p")


# --------------------------------------------------------------------------- #
# Theme / palette per app
# --------------------------------------------------------------------------- #
APP_META = {
    "gpay":    {"name": "Google Pay", "accent": (26, 115, 232)},
    "phonepe": {"name": "PhonePe",    "accent": (93, 46, 140)},
    "paytm":   {"name": "Paytm",      "accent": (0, 186, 241)},
    "bhim":    {"name": "BHIM",       "accent": (240, 110, 40)},
    "bank":    {"name": "Bank UPI",   "accent": (0, 128, 96)},
}


def palette(theme):
    if theme == "dark":
        return {"bg": (18, 18, 20), "card": (32, 33, 38),
                "text": (240, 240, 245), "muted": (150, 152, 160),
                "ok": (65, 200, 120), "fail": (255, 82, 82),
                "pending": (255, 179, 0), "info": (100, 181, 246)}
    return {"bg": (245, 246, 248), "card": (255, 255, 255),
            "text": (28, 30, 34), "muted": (120, 124, 132),
            "ok": (30, 160, 90), "fail": (211, 47, 47),
            "pending": (214, 137, 16), "info": (33, 118, 214)}


# --------------------------------------------------------------------------- #
# Drawing helpers that also record bounding boxes
# --------------------------------------------------------------------------- #
def draw_field(draw, xy, text, fnt, fill, field, boxes, anchor="la"):
    """Draw text, record its bbox + field name/value."""
    text = str(text)
    bbox = draw.textbbox(xy, text, font=fnt, anchor=anchor)
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)
    boxes.append({
        "field": field,
        "text": text,
        "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
    })
    return bbox


# --------------------------------------------------------------------------- #
# Status glyphs  --  drawn inside the status circle, in white
# --------------------------------------------------------------------------- #
WHITE = (255, 255, 255)


def glyph_tick(d, cx, cy, r, color):
    d.line([cx - 42, cy, cx - 10, cy + 36], fill=color, width=14)
    d.line([cx - 10, cy + 36, cx + 48, cy - 34], fill=color, width=14)


def glyph_cross(d, cx, cy, r, color):
    o = 38
    d.line([cx - o, cy - o, cx + o, cy + o], fill=color, width=14)
    d.line([cx + o, cy - o, cx - o, cy + o], fill=color, width=14)


def glyph_clock(d, cx, cy, r, color):
    d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], outline=color, width=12)
    d.line([cx, cy - 26, cx, cy + 4], fill=color, width=12)      # hour hand
    d.line([cx, cy + 4, cx + 24, cy + 16], fill=color, width=12)  # minute hand


def glyph_undo(d, cx, cy, r, color):
    # arc with a gap at the top-left, plus an arrow head
    d.arc([cx - 46, cy - 46, cx + 46, cy + 46], start=140, end=430, fill=color, width=12)
    d.polygon([(cx - 52, cy - 54), (cx - 16, cy - 44), (cx - 46, cy - 20)], fill=color)


def glyph_spinner(d, cx, cy, r, color):
    # three dots tapering in size, like a loading indicator
    for dy, dot in ((-34, 16), (0, 13), (34, 10)):
        d.ellipse([cx - dot, cy + dy - dot, cx + dot, cy + dy + dot], fill=color)


GLYPHS = {
    "tick": glyph_tick,
    "cross": glyph_cross,
    "clock": glyph_clock,
    "undo": glyph_undo,
    "spinner": glyph_spinner,
}


# --------------------------------------------------------------------------- #
# Receipt renderer
# --------------------------------------------------------------------------- #
def render(app, theme, status):
    meta = APP_META[app]
    pal = palette(theme)
    smeta = STATUS_META[status]
    color = pal[smeta["color_key"]]
    W, H = IMG_SIZE

    img = Image.new("RGB", (W, H), pal["bg"])
    d = ImageDraw.Draw(img)
    boxes = []

    # sample data
    payee_name = rand_name()
    merchant = random.choice(MERCHANTS)
    if merchant:
        payee_name = merchant
    payee_vpa = rand_vpa(payee_name if not merchant else random.choice(FIRST))
    payer_name = rand_name()
    payer_bank = random.choice(BANKS)
    acct_tail = "".join(random.choices(string.digits, k=4))
    amount = rand_amount()
    txn_id = rand_txn_id(app)
    when = rand_datetime()

    # failed / pending receipts carry a reason instead of (or alongside) a UTR
    reason = random.choice(FAILURE_REASONS) if status in ("Payment Failed", "Pending") else None
    utr = rand_utr() if smeta["has_utr"] else ""
    utr_display = utr if utr else "Not available"
    amount_display = f"{smeta['amount_sign']}\u20b9{amount}"

    fields = {
        "app": meta["name"], "theme": theme, "status": status,
        "amount": amount, "amount_display": amount_display,
        "payee_name": payee_name, "payee_vpa": payee_vpa,
        "payer_name": payer_name, "payer_bank": payer_bank,
        "account_tail": "XXXX" + acct_tail,
        "utr": utr, "has_utr": smeta["has_utr"],
        "transaction_id": txn_id, "datetime": when,
        "status_reason": reason or "",
    }

    # ---- top app bar
    d.rectangle([0, 0, W, 150], fill=meta["accent"])
    draw_field(d, (W // 2, 75), meta["name"], font(48, bold=True),
               (255, 255, 255), "app", boxes, anchor="mm")

    # ---- status badge circle + glyph
    cx, cy, r = W // 2, 340, 90
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    GLYPHS[smeta["glyph"]](d, cx, cy, r, WHITE)

    draw_field(d, (cx, cy + 150), smeta["headline"], font(50, bold=True),
               color, "status", boxes, anchor="mm")

    # ---- amount
    draw_field(d, (cx, cy + 258), amount_display, font(92, bold=True),
               pal["text"], "amount", boxes, anchor="mm")

    # ---- helper line under the amount
    if smeta["note"]:
        draw_field(d, (cx, cy + 320), smeta["note"], font(30),
                   pal["muted"], "status_note", boxes, anchor="mm")

    # ---- details card
    card_top = cy + 400
    rows = [
        ("Paid to",          payee_name,        "payee_name"),
        ("UPI ID",           payee_vpa,         "payee_vpa"),
        ("From",             payer_name,        "payer_name"),
        ("Bank",             f"{payer_bank}  XXXX{acct_tail}", "payer_bank"),
        ("Date",             when,              "datetime"),
        ("UPI transaction ID", utr_display,     "utr"),
        (f"{meta['name']} txn ID", txn_id,      "transaction_id"),
    ]
    if reason:
        rows.insert(6, ("Reason", reason, "status_reason"))

    card_h = 110 + 112 * len(rows)
    d.rounded_rectangle([60, card_top, W - 60, card_top + card_h],
                        radius=36, fill=pal["card"])

    y = card_top + 70
    for i, (label, value, key) in enumerate(rows):
        draw_field(d, (110, y), label, font(34), pal["muted"], f"{key}_label", boxes)
        if key == "status_reason":
            draw_field(d, (W - 110, y + 44), value, font(34, bold=True),
                       color, key, boxes, anchor="ra")
        else:
            draw_field(d, (W - 110, y + 44), value, font(40, bold=True),
                       pal["text"], key, boxes, anchor="ra")
        y += 112
        if i < len(rows) - 1:
            d.line([110, y - 20, W - 110, y - 20], fill=pal["muted"], width=1)

    # ---- footer
    draw_field(d, (cx, H - 90), "Powered by UPI", font(32), pal["muted"],
               "footer", boxes, anchor="mm")

    return img, fields, boxes


# --------------------------------------------------------------------------- #
# Augmentation
# --------------------------------------------------------------------------- #
def augment(img):
    # slight rotation
    if random.random() < 0.6:
        angle = random.uniform(-3, 3)
        img = img.rotate(angle, expand=False,
                         fillcolor=(random.randint(0, 40),) * 3)
    # blur
    if random.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(random.uniform(0.4, 1.6)))
    # gaussian noise
    if random.random() < 0.5:
        import struct
        px = img.load()
        W, H = img.size
        for _ in range(int(W * H * 0.02)):
            x, y = random.randint(0, W - 1), random.randint(0, H - 1)
            n = random.randint(-30, 30)
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + n)),
                        max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    return img


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    img_dir = os.path.join(OUT_DIR, "images")
    ann_dir = os.path.join(OUT_DIR, "annotations")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(ann_dir, exist_ok=True)

    jsonl_path = os.path.join(OUT_DIR, "labels.jsonl")
    csv_path = os.path.join(OUT_DIR, "labels.csv")

    csv_fields = ["image", "app", "theme", "status", "status_reason",
                  "amount", "amount_display", "payee_name", "payee_vpa",
                  "payer_name", "payer_bank", "account_tail", "has_utr",
                  "utr", "transaction_id", "datetime"]

    if _REG_PATH is None:
        print("[warn] No TrueType font found; using PIL default (\u20b9 may not render).")

    counts = {"status": {}, "app": {}, "theme": {}}

    with open(jsonl_path, "w", encoding="utf-8") as jf, \
         open(csv_path, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_fields)
        writer.writeheader()

        for i in range(NUM_IMAGES):
            app = APPS[i % len(APPS)]
            theme = random.choice(THEMES)
            status = pick_status()
            img, fields, boxes = render(app, theme, status)

            counts["status"][status] = counts["status"].get(status, 0) + 1
            counts["app"][fields["app"]] = counts["app"].get(fields["app"], 0) + 1
            counts["theme"][theme] = counts["theme"].get(theme, 0) + 1

            augmented = random.random() < AUGMENT_RATIO
            if augmented:
                img = augment(img)

            stem = f"{app}_{status_slug(status)}_{theme}_{i:05d}"
            fname = stem + ".jpg"
            img.save(os.path.join(img_dir, fname), "JPEG",
                     quality=random.randint(*JPEG_QUALITY))

            record = {
                "image": fname,
                "app": app,
                "status": status,
                "theme": theme,
                "augmented": augmented,
                "fields": fields,
                "boxes": boxes,
            }
            with open(os.path.join(ann_dir, stem + ".json"), "w",
                      encoding="utf-8") as af:
                json.dump(record, af, ensure_ascii=False, indent=2)

            jf.write(json.dumps(record, ensure_ascii=False) + "\n")
            writer.writerow({"image": fname, **{k: fields.get(k, "")
                                                for k in csv_fields if k != "image"}})

            if (i + 1) % 50 == 0:
                print(f"  generated {i + 1}/{NUM_IMAGES}")

    summary_path = os.path.join(OUT_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump({"total": NUM_IMAGES, "seed": SEED, **counts}, sf, indent=2)

    print(f"\nDone. {NUM_IMAGES} images in {img_dir}")
    print(f"Labels: {jsonl_path}")
    print(f"        {csv_path}")
    print(f"Per-image JSON (fields + bboxes): {ann_dir}")
    print(f"Summary: {summary_path}")
    for key, table in counts.items():
        print(f"  {key}: " + ", ".join(f"{k}={v}" for k, v in sorted(table.items())))


if __name__ == "__main__":
    main()
