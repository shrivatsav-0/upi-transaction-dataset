"""Dataset orchestration: build each sample, render it, write the labels."""

from __future__ import annotations

import csv
import json
import os
import random
from collections import Counter, defaultdict

from . import chrome, config, data, layouts
from .canvas import Canvas
from .fonts import FontBook

# Flat columns for labels.csv, in order.
CSV_FIELDS = [
    "image", "app", "app_key", "theme", "frame", "layout",
    "status", "status_text", "status_reason",
    "amount", "amount_display", "currency",
    "payee_name", "payee_vpa", "vpa_style", "vpa_visible",
    "payer_name", "payer_bank", "account_tail",
    "utr", "has_utr", "txn_id", "txn_id_label", "datetime",
]


class DatasetWriter:
    def __init__(self, settings: config.Settings):
        self.settings = settings
        self.img_dir = os.path.join(settings.out_dir, "images")
        self.ann_dir = os.path.join(settings.out_dir, "annotations")
        os.makedirs(self.img_dir, exist_ok=True)
        os.makedirs(self.ann_dir, exist_ok=True)
        self.fonts = FontBook()
        self.dropped_boxes = 0

    # -- public -------------------------------------------------------------
    def generate(self, progress_every: int = 50) -> dict:
        rng = random.Random(self.settings.seed)
        counts: dict[str, Counter] = defaultdict(Counter)

        jsonl_path = os.path.join(self.settings.out_dir, "labels.jsonl")
        csv_path = os.path.join(self.settings.out_dir, "labels.csv")

        with open(jsonl_path, "w", encoding="utf-8") as jf, \
             open(csv_path, "w", encoding="utf-8", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=CSV_FIELDS)
            writer.writeheader()

            for i in range(self.settings.num_images):
                txn = data.make_transaction(rng, self.settings)
                app = config.APPS[txn.app_key]

                record, csv_row = self._render_one(rng, i, txn, app)
                self._tally(counts, txn, record)

                jf.write(json.dumps(record, ensure_ascii=False) + "\n")
                writer.writerow(csv_row)

                if progress_every and (i + 1) % progress_every == 0:
                    print(f"  generated {i + 1}/{self.settings.num_images}")

        summary = {
            "total": self.settings.num_images,
            "seed": self.settings.seed,
            "apps": dict(sorted(counts["app"].items())),
            "themes": dict(sorted(counts["theme"].items())),
            "frames": dict(sorted(counts["frame"].items())),
            "statuses": dict(sorted(counts["status"].items())),
            "status_texts": dict(sorted(counts["status_text"].items())),
            "vpa_styles": dict(sorted(counts["vpa_style"].items())),
            "currencies": dict(sorted(counts["currency"].items())),
            "augmented": counts["augmented"]["yes"],
            "dropped_boxes": self.dropped_boxes,
        }
        with open(os.path.join(self.settings.out_dir, "summary.json"), "w",
                  encoding="utf-8") as sf:
            json.dump(summary, sf, indent=2, ensure_ascii=False)
        return summary

    # -- internals ----------------------------------------------------------
    def _render_one(self, rng, index, txn, app):
        pal = config.PALETTES[txn.theme]
        boxes: list[dict] = []
        c = Canvas(self.settings.img_size, pal.bg, boxes, self.fonts)

        frame = chrome.Frame(txn.frame)
        if frame.has_status_bar:
            chrome.draw_status_bar(c, pal, data.rand_clock(rng), rng.randint(18, 100))
            chrome.draw_nav_bar(c, pal,
                                style=rng.choice(["gesture", "gesture", "buttons"]))

        layouts.renderer_for(app.layout)(c, app, txn.theme, txn, frame, rng)

        # Safety net: an expanded accordion can run past the nav bar on a tall
        # card. Drop those bboxes rather than pointing at clipped glyphs, and
        # surface the count in summary.json so the loss is never silent.
        limit = c.h - frame.bottom if frame.bottom else c.h
        kept = [b for b in boxes if b["bbox"][3] <= limit]
        self.dropped_boxes += len(boxes) - len(kept)
        boxes = kept

        stem = (f"{app.key}_{_slug(txn.status_label)}_{txn.theme}"
                f"_{txn.frame}_{index:05d}")
        fname = stem + ".jpg"

        augmented = rng.random() < self.settings.augment_ratio
        out = c.augmented(rng) if augmented else c.img
        out.save(os.path.join(self.img_dir, fname), "JPEG",
                 quality=rng.randint(*self.settings.jpeg_quality))

        record = {
            "image": fname,
            "app": txn.app_name,
            "app_key": app.key,
            "theme": txn.theme,
            "frame": txn.frame,
            "layout": app.layout,
            "status": txn.status_label,
            "status_bucket": txn.status,
            "status_text": txn.status_text,
            "augmented": augmented,
            # Not every field is on screen: a collapsed GPay accordion hides the
            # details, and Paytm renders the amount inside a sentence. This is
            # the authoritative list of what a detector is expected to find.
            "visible_fields": sorted({b["field"] for b in boxes}),
            "fields": txn.as_fields(),
            "boxes": boxes,
        }

        with open(os.path.join(self.ann_dir, stem + ".json"), "w",
                  encoding="utf-8") as af:
            json.dump(record, af, ensure_ascii=False, indent=2)
        return record, self._csv_row(fname, txn, app)

    @staticmethod
    def _csv_row(fname, txn, app) -> dict:
        return {
            "image": fname,
            "app": txn.app_name,
            "app_key": app.key,
            "theme": txn.theme,
            "frame": txn.frame,
            "layout": app.layout,
            "status": txn.status_label,
            "status_text": txn.status_text,
            "status_reason": txn.status_reason,
            "amount": f"{txn.amount:.2f}",
            "amount_display": txn.amount_display,
            "currency": txn.currency,
            "payee_name": txn.payee_name,
            "payee_vpa": txn.payee_vpa,
            "vpa_style": txn.vpa_style,
            "vpa_visible": txn.vpa_visible,
            "payer_name": txn.payer_name,
            "payer_bank": txn.payer_bank,
            "account_tail": txn.account_tail,
            "utr": txn.utr,
            "has_utr": txn.has_utr,
            "txn_id": txn.txn_id,
            "txn_id_label": txn.txn_id_label,
            "datetime": txn.datetime_text,
        }

    @staticmethod
    def _tally(counts, txn, record):
        counts["app"][txn.app_name] += 1
        counts["theme"][txn.theme] += 1
        counts["frame"][txn.frame] += 1
        counts["status"][txn.status_label] += 1
        counts["status_text"][txn.status_text] += 1
        counts["vpa_style"][txn.vpa_style] += 1
        counts["currency"][txn.currency] += 1
        counts["augmented"]["yes" if record["augmented"] else "no"] += 1


def _slug(text: str) -> str:
    return text.lower().replace(" ", "_")