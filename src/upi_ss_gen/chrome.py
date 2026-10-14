"""Device chrome: the Android status bar and navigation bar.

These are what separate a "full screenshot" sample from a "tightly cropped
receipt card" sample -- one of the layout axes in the spec.
"""

from __future__ import annotations

from . import icons

STATUS_BAR_H = 96
NAV_BAR_H = 84


class Frame:
    """Reserved space at the top/bottom of the canvas for device chrome."""

    def __init__(self, mode: str):
        self.mode = mode
        self.top = STATUS_BAR_H if mode == "full" else 0
        self.bottom = NAV_BAR_H if mode == "full" else 0

    @property
    def has_status_bar(self) -> bool:
        return self.mode == "full"


def draw_status_bar(c, palette, clock_text: str, battery_level: int):
    """Time on the left; signal, wifi and battery on the right."""
    h = STATUS_BAR_H
    mid = h // 2

    c.rect([0, 0, c.w, h], fill=palette.bg)

    c.text((44, mid), clock_text, 30, palette.text, "chrome_clock", anchor="lm")

    right = c.w - 40

    # Lay the right-hand widgets out right-to-left from the measured text width,
    # so nothing overlaps whatever the percentage reads.
    pct = f"{battery_level}%"
    pct_w = c.width_of(pct, 26)
    c.text((right, mid), pct, 26, palette.muted, "chrome_battery_pct",
           anchor="rm")

    battery_x = right - pct_w - 18 - 63          # 54px body + 9px nub
    icons.battery(c, battery_x, mid, palette.text, level=battery_level / 100.0)

    wifi_cx = battery_x - 52
    icons.wifi_arcs(c, wifi_cx, mid, palette.text)

    icons.signal_bars(c, wifi_cx - 42 - 4 * 17, mid, palette.text)


def draw_nav_bar(c, palette, style: str = "gesture"):
    """Gesture pill or the classic three-button bar."""
    y0 = c.h - NAV_BAR_H
    c.rect([0, y0, c.w, c.h], fill=palette.bg)

    mid = y0 + NAV_BAR_H // 2

    if style == "gesture":
        w, h = 300, 14
        c.rounded([c.w // 2 - w // 2, mid - h // 2, c.w // 2 + w // 2, mid + h // 2],
                  radius=h // 2, fill=palette.text)
    else:
        # back / home / recents
        back_x = c.w // 2 - 180
        icons.back_arrow(c, back_x, mid, palette.text, width=7)

        c.ellipse([c.w // 2 - 27, mid - 27, c.w // 2 + 27, mid + 27],
                  outline=palette.text, width=6)

        recents = c.w // 2 + 150
        s = 24
        c.rounded([recents - s, mid - s, recents + s, mid + s], radius=8,
                  outline=palette.text, width=6)