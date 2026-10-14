# UPI / PayPal Receipt Dataset Generator

Synthetic payment-receipt screenshots for training and benchmarking OCR and
document-AI models on Indian payment UIs. Every image ships with ground-truth
field values **and** bounding boxes.

Nothing here is scraped or real. Names, VPAs, phone numbers, account tails,
banks and transactions are all randomly generated. This exists so you can train
without collecting real screenshots, which carry PII and have no labels.

## Install & run

```bash
uv sync
uv run upi-ss-gen                      # 600 images -> ./dataset
uv run upi-ss-gen -n 2000 --seed 7     # bigger run, reproducible
uv run upi-ss-gen --no-augment         # pristine renders, no rotation/blur
uv run upi-ss-gen -o ./mydata --size 720x1280
```

`python upi_receipt_generator.py` works too and forwards the same flags.

## Output

```
dataset/
  images/<app>_<status>_<theme>_<frame>_<id>.jpg
  annotations/<same>.json     per-image fields + boxes
  labels.jsonl                one record per line
  labels.csv                  flat table
  summary.json                counts per axis
```

`dataset/` is git-ignored, so generated output never lands in a commit.

### Annotation format

```json
{
  "image": "gpay_payment_failed_light_full_00058.jpg",
  "app": "Google Pay",
  "status": "Payment Failed",
  "status_bucket": "failed",
  "status_text": "Payment could not be completed",
  "visible_fields": ["amount", "payee_name", "status", "utr", "..."],
  "fields": {
    "amount_display": "₹ 8,835",
    "payee_name_display": "Cafe Coffee Day",
    "payee_vpa": "sneha473@upi",
    "status_reason": "Internet connectivity lost",
    "utr": "..."
  },
  "boxes": [
    {"field": "amount", "text": "₹ 8,835", "bbox": [372, 566, 709, 670]}
  ]
}
```

`fields` holds every generated value. `boxes` holds only what is actually
painted on screen, so a collapsed accordion or an inline sentence cannot
produce a bbox for text the user cannot see. Use **`visible_fields`** as the
authoritative list of what a detector should find in that image.

## Variation axes

Six independent axes, each weighted in `config.Settings`:

**1. Recipient & VPA masking** — for training a fuzzy/masked VPA matcher.
| `vpa_style` | Example |
|---|---|
| `plain` | `sharan.s123@okhdfc` |
| `stars_mid` | `sharan***23@okhdfc` |
| `stars_lead` | `s********@okaxis` |
| `x_mid` | `98765XXXX0@paytm` |
| `name_only` | no VPA at all — account tail `A/c XXXX1234` instead |
| `truncated` | name or VPA cut with an ellipsis |

**2. Status** — four buckets, each with several real-world phrasings.
`Payment Successful`, `Payment Pending`, `Payment Failed`, `Payment Reversed`,
rendered as *"Paid successfully"*, *"Awaiting bank confirmation"*, *"Bank server
issue"*, *"Refund processed"*, … PayPal gets its own set (*"Completed"*,
*"Refunded"*). Failed receipts drop the UTR and gain a failure reason;
reversed receipts show a negative amount.

**3. Layout** — one renderer per app family.
`gpay` hero amount + expandable accordion · `phonepe` purple card, two-column,
separate txn ID and UTR · `paytm` blue banner with inline sentence and a UPI Ref
No strip below · `tabular` bordered slip (Cred, BHIM, bank) · `paypal`.
Each is sampled as `full` (status bar + nav bar) or `cropped` (card only).

**4. Amount & date formats** — `₹1500`, `₹ 1500`, `₹1,500.50`, `₹1,23,456.00`
(Indian lakh/crore grouping), `INR 1,500`, `Rs. 1500`; dates as
`12 Oct 2026, 4:12 pm`, `12/10/2026 at 16:12:03`, `Oct 12, 2026 04:12 PM IST`,
`12-10-2026, 16:12`. PayPal uses `$`/`€`/`£` or an `USD 255.00` code form.

**5. PayPal** — 17-character alphanumeric transaction IDs, `@handle` or email
recipients, `You sent $X to ...`, currency labels.

**6. Themes & augmentation** — light and dark; random rotation, blur and
speckle noise on 60% of images.

## Layout of the code

```
src/upi_ss_gen/
  config.py     apps, statuses, palettes, weights  <- tune here
  formats.py    amount + date formatting, VPA masking
  data.py       fake-data generation, Transaction dataclass
  canvas.py     drawing surface that records a bbox per label
  icons.py      status glyphs, avatars, status-bar widgets
  chrome.py     status bar / nav bar
  layouts/      one module per app family
  dataset.py    orchestration and label writers
  cli.py        argument parsing
```

Adding an app is an `AppSpec` in `config.py` plus a renderer in `layouts/`.