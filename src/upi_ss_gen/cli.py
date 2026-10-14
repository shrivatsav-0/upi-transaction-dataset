"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import sys

from .config import Settings
from .dataset import DatasetWriter


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="upi-ss-gen",
        description="Generate a synthetic UPI / PayPal receipt dataset for OCR training.",
    )
    p.add_argument("-n", "--num-images", type=int, default=600,
                   help="how many screenshots to generate (default: 600)")
    p.add_argument("-s", "--seed", type=int, default=42,
                   help="random seed -- same seed reproduces the dataset exactly")
    p.add_argument("-o", "--out", default=None,
                   help="output directory (default: ./dataset)")
    p.add_argument("--size", default="1080x2000",
                   help="canvas size, WxH (default: 1080x2000)")
    p.add_argument("--no-augment", action="store_true",
                   help="skip rotation/blur/noise so every image is pristine")
    p.add_argument("--quiet", action="store_true", help="suppress progress output")
    return p


def parse_size(text: str) -> tuple[int, int]:
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected WxH, e.g. 1080x2000 (got {text!r})")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "dataset")

    settings = Settings(
        num_images=args.num_images,
        seed=args.seed,
        out_dir=out_dir,
        img_size=parse_size(args.size),
        augment_ratio=0.0 if args.no_augment else 0.6,
    )

    writer = DatasetWriter(settings)
    if not writer.fonts.has_true_type:
        print("[warn] No TrueType font found; falling back to the PIL default "
              "(the rupee glyph will not render).", file=sys.stderr)

    if not args.quiet:
        print(f"Generating {settings.num_images} images into {out_dir}")

    summary = writer.generate(progress_every=0 if args.quiet else 50)

    if not args.quiet:
        print(f"\nDone. {settings.num_images} images in {writer.img_dir}")
        for key in ("apps", "themes", "frames", "statuses", "vpa_styles",
                    "currencies"):
            table = summary[key]
            pretty = ", ".join(f"{k}={v}" for k, v in table.items())
            print(f"  {key:<12} {pretty}")
        if summary["dropped_boxes"]:
            print(f"  note: {summary['dropped_boxes']} bboxes clipped past the "
                  f"nav bar and were dropped")
    return 0