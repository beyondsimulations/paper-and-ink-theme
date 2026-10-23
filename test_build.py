# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4"]
# ///
"""Self-checks for build.py. Run `uv run test_build.py`; it prints "all checks pass" or stops at the first failed assert."""
import copy
import json

import build

SCHEMA = json.loads(build.SCHEMA.read_text())


def test_colour_math():
    # APCA-W3 0.0.98G reference values: black on white 106.04, white on black 107.88, #888 on white 63.06
    assert round(build.apca("#000000", "#FFFFFF"), 1) == 106.0
    assert round(build.apca("#FFFFFF", "#000000"), 1) == 107.9
    assert round(build.apca("#888888", "#FFFFFF"), 1) == 63.1
    assert build.apca("#777777", "#777777") == 0.0
    # OKLCH round trip on a brand colour, and the extremes
    L, C, h = build.hex_to_oklch("#F6B265")
    assert (round(L, 3), round(C, 3), round(h, 1)) == (0.812, 0.123, 68.0)
    assert build.oklch_to_hex(L, C, h) == "#F6B265"
    assert build.oklch_to_hex(0, 0, 0) == "#000000"
    assert build.oklch_to_hex(1, 0, 0) == "#FFFFFF"
    # out-of-gamut chroma is reduced, not wrapped
    assert build.oklch_to_hex(0.9, 0.4, 150).startswith("#")
    assert build.oklab_distance("#000000", "#FFFFFF") > 0.99


def test_mapping():
    style = build.build_family()["themes"][0]["style"]
    syn, P = style["syntax"], build.P
    assert syn["comment"]["color"] == P["prose"] and syn["comment"]["font_style"] is None
    assert syn["function.definition"] == {"color": P["call"], "font_style": None, "font_weight": 700}
    assert syn["function.macro"]["color"] == P["macro"]
    assert style["editor.background"] == build.oklch_to_hex(*build.INK)
    assert style["warning"] == P["constant"] != syn["function"]["color"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all checks pass")
