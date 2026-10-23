# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4"]
# ///
"""Build themes/paper-and-ink.json from the OKLCH palette below, then check it.

Run `uv run build.py`. It exits 1 and lists every failed check.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "themes" / "paper-and-ink.json"
SCHEMA = ROOT / "schema" / "theme-v0.2.0.json"


# ---- colour math: OKLab/OKLCH (Björn Ottosson) and APCA-W3 0.0.98G ----

def _to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_gamma(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb(hex_):
    h = hex_.lstrip("#")
    assert len(h) == 6, f"opaque colour expected, got {hex_}"
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _oklab(hex_):
    r, g, b = (_to_linear(c) for c in _rgb(hex_))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def hex_to_oklch(hex_):
    L, a, b = _oklab(hex_)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_to_hex(L, C, h):
    """sRGB hex for an OKLCH colour; lowers chroma until the colour fits sRGB."""
    while True:
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
               -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
               -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
        if C <= 0 or all(-1e-4 <= c <= 1 + 1e-4 for c in rgb):
            return "#" + "".join(f"{round(min(1, max(0, _to_gamma(max(0, c)))) * 255):02X}" for c in rgb)
        C -= 0.002


def oklab_distance(hex_a, hex_b):
    return math.dist(_oklab(hex_a), _oklab(hex_b))


def apca(text, bg):
    """Absolute APCA lightness contrast Lc of text on bg (0 to about 108)."""
    def y(hex_):
        r, g, b = (c ** 2.4 for c in _rgb(hex_))
        v = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        return v + (0.022 - v) ** 1.414 if v < 0.022 else v
    yt, yb = y(text), y(bg)
    if abs(yb - yt) < 0.0005:
        return 0.0
    if yb > yt:
        s = (yb ** 0.56 - yt ** 0.57) * 1.14
        return 0.0 if s < 0.1 else (s - 0.027) * 100
    s = (yb ** 0.65 - yt ** 0.62) * 1.14
    return 0.0 if s > -0.1 else -(s + 0.027) * 100
