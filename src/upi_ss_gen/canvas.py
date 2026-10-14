"""Canvas: a thin wrapper over PIL that records a bbox per drawn label."""

from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFilter

from .fonts import FontBook


class Canvas:
    """Wraps an RGB image and a draw context.

    `text()` is the only call that appends to the annotation list, so every bbox
    in labels.jsonl corresponds to a real glyph run that OCR can be scored on.
    """

    def __init__(self, size, bg, boxes, fonts: FontBook):
        self.size = size
        self.w, self.h = size
        self.img = Image.new("RGB", size, bg)
        self.d = ImageDraw.Draw(self.img)
        self.boxes = boxes
        self.fonts = fonts

    # -- text ---------------------------------------------------------------
    def text(self, xy, text, size, fill, field, *, bold=False, anchor="la",
             record=True, font=None):
        """Draw text and (by default) record its bbox under `field`.

        Returns the advance width in pixels, or None for empty strings.
        """
        text = "" if text is None else str(text)
        if not text:
            return None
        fnt = font or self.fonts(size, bold)
        self.d.text(xy, text, font=fnt, fill=fill, anchor=anchor)
        width = int(self.d.textbbox((0, 0), text, font=fnt)[2])
        if record:
            bbox = self.d.textbbox(xy, text, font=fnt, anchor=anchor)
            self.boxes.append({
                "field": field,
                "text": text,
                "bbox": [int(v) for v in bbox],
            })
        return width

    def width_of(self, text, size, bold=False) -> int:
        """Advance width of `text` without drawing it (for right-alignment)."""
        return int(self.d.textbbox((0, 0), str(text), font=self.fonts(size, bold))[2])

    # -- shapes -------------------------------------------------------------
    # PIL rejects float coordinates, so the glyphs' radius-relative maths is
    # rounded here rather than at every call site.
    @staticmethod
    def _box(box):
        return [round(v) for v in box]

    @staticmethod
    def _pts(points):
        """Accepts either a flat [x0, y0, x1, y1] list or a list of pairs."""
        if points and not isinstance(points[0], (tuple, list)):
            return [(round(points[i]), round(points[i + 1]))
                    for i in range(0, len(points) - 1, 2)]
        return [(round(x), round(y)) for x, y in points]

    def rect(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(self._box(box), fill=fill, outline=outline,
                         width=round(width))

    def rounded(self, box, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._box(box), radius=round(radius), fill=fill,
                                 outline=outline, width=round(width))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(self._box(box), fill=fill, outline=outline,
                        width=round(width))

    def line(self, points, fill, width=1):
        self.d.line(self._pts(points), fill=fill, width=round(width))

    def arc(self, box, start, end, fill, width=1):
        self.d.arc(self._box(box), start=start, end=end, fill=fill,
                   width=round(width))

    def polygon(self, points, fill=None, outline=None):
        self.d.polygon(self._pts(points), fill=fill, outline=outline)

    def pieslice(self, box, start, end, fill=None, outline=None):
        self.d.pieslice(self._box(box), start=start, end=end, fill=fill,
                        outline=outline)

    def hairline(self, y, x0, x1, fill):
        """1px separator -- cheap, but drawn at width 2 so JPEG keeps it."""
        self.d.line(self._pts([(x0, y), (x1, y)]), fill=fill, width=2)

    def save_jpeg(self, path, quality):
        self.img.save(path, "JPEG", quality=quality)

    # -- augmentation -------------------------------------------------------
    def augmented(self, rng: random.Random) -> Image.Image:
        """Rotation + blur + speckle noise, mimicking a re-shot photo/screenshot."""
        out = self.img

        if rng.random() < 0.6:
            angle = rng.uniform(-3, 3)
            border = (rng.randint(0, 40),) * 3
            out = out.rotate(angle, expand=False, fillcolor=border)

        if rng.random() < 0.5:
            out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.6)))

        if rng.random() < 0.5:
            px = out.load()
            w, h = out.size
            amp = rng.randint(18, 32)
            for _ in range(int(w * h * 0.02)):
                x = rng.randrange(w)
                y = rng.randrange(h)
                r, g, b = px[x, y]
                delta = rng.randint(-amp, amp)
                px[x, y] = (max(0, min(255, r + delta)),
                            max(0, min(255, g + delta)),
                            max(0, min(255, b + delta)))
        return out