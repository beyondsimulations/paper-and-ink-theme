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
    # WCAG 2 contrast ratio: black on white 21:1, #777 on white 4.48:1 (just under AA)
    assert round(build.wcag("#000000", "#FFFFFF"), 2) == 21.0
    assert round(build.wcag("#777777", "#FFFFFF"), 2) == round(build.wcag("#FFFFFF", "#777777"), 2) == 4.48
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
    family = build.build_family()
    assert [(t["name"], t["appearance"]) for t in family["themes"]] == [
        ("Paper & Ink Dark", "dark"), ("Paper & Ink Light", "light")]
    for theme, t in zip(build.THEMES, family["themes"]):
        style, syn, P = t["style"], t["style"]["syntax"], build.hexes(theme)
        # the prose is set in italic: that, not the colour, sets it apart from the code
        for key in ("comment", "comment.doc"):
            assert syn[key] == {"color": P["prose"], "font_style": "italic", "font_weight": None}
        assert style["text"] == P["prose"]
        assert syn["function.definition"] == {"color": P["call"], "font_style": None, "font_weight": 700}
        assert syn["function.macro"]["color"] == P["macro"]
        assert style["warning"] == P["constant"] != syn["function"]["color"]
    dark, light = (t["style"] for t in family["themes"])
    assert dark["editor.background"] == "#161311"
    assert light["editor.background"] == "#FFFDFC"  # the website's page colour
    # panels sit below the editor in both: deeper than the ink, greyer than the paper
    for style in (dark, light):
        assert build.hex_to_oklch(style["panel.background"])[0] < build.hex_to_oklch(style["editor.background"])[0]


def test_real_theme_passes():
    assert build.check(build.build_family(), SCHEMA) == []


def broken(path, value, theme=0):
    family = build.build_family()
    target = family["themes"][theme]["style"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return build.check(family, SCHEMA)


def test_checks_catch_failures():
    P = build.hexes(build.DARK)
    dim = build.oklch_to_hex(0.55, 0.01, 70)
    assert any(f.startswith("Paper & Ink Dark: contrast: prose") for f in broken(["syntax", "comment", "color"], dim))
    # code in the prose colour: contrast is fine, but the two can no longer be told apart
    assert any("prose and code" in f for f in broken(["editor.foreground"], P["prose"]))
    assert any("call and constant" in f for f in broken(["syntax", "function", "color"], P["constant"]))
    assert any("error and macro" in f for f in broken(["error"], P["macro"]))
    # the light theme is checked too, against its own paper
    pale = build.oklch_to_hex(0.75, 0.01, 60)
    assert any(f.startswith("Paper & Ink Light: contrast: prose") for f in broken(["syntax", "comment", "color"], pale, theme=1))
    # WCAG AA too: the first light orange passed APCA but not 4.5:1
    assert any(f.startswith("Paper & Ink Light: wcag: constant") for f in broken(["syntax", "number", "color"], "#BC5B03", theme=1))
    family = build.build_family()
    del family["themes"][1]["style"]["editor.indent_guide"]
    assert "Paper & Ink Light: missing key: editor.indent_guide" in build.check(family, SCHEMA)
    assert any(f.startswith("schema") for f in broken(["syntax", "comment", "font_weight"], 450))
    # the checks must not mutate the family they inspect
    family = build.build_family()
    snapshot = copy.deepcopy(family)
    build.check(family, SCHEMA)
    assert family == snapshot


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all checks pass")
