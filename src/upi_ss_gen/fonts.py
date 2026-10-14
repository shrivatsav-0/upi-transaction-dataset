"""Font discovery with a size cache."""

from __future__ import annotations

import os

from PIL import ImageFont

_REG_CANDIDATES = [
    r"C:\Windows\Fonts\segoeui.ttf",          # ships the ₹ glyph
    r"C:\Windows\Fonts\segoeuiem.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\segoeuiz.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


class FontBook:
    """`fonts(34)` / `fonts(34, bold=True)` returns a cached TrueType font."""

    def __init__(self):
        self.reg_path = _first_existing(_REG_CANDIDATES)
        self.bold_path = _first_existing(_BOLD_CANDIDATES) or self.reg_path
        self._cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}
        self.has_true_type = self.reg_path is not None

    def __call__(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        key = (size, bold)
        if key not in self._cache:
            path = self.bold_path if bold else self.reg_path
            if path:
                self._cache[key] = ImageFont.truetype(path, size)
            else:
                self._cache[key] = ImageFont.load_default()
        return self._cache[key]