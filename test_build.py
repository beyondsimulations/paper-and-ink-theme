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
    # alpha compositing over an opaque background
    assert build.blend("#FF000080", "#000000") == "#800000"
    assert build.blend("#FF0000", "#00FF00") == "#FF0000"


def test_mapping():
    family = build.build_family()
    assert [(t["name"], t["appearance"]) for t in family["themes"]] == [
        ("Paper & Ink Dark", "dark"), ("Paper & Ink Light", "light")]
    for theme, t in zip(build.THEMES, family["themes"]):
        style, syn, P = t["style"], t["style"]["syntax"], build.hexes(theme)
        # the prose is set in italic: that, not the colour, sets it apart from the code
        for key in ("comment", "comment.doc"):
            assert syn[key] == {"color": P["prose"], "font_style": "italic", "font_weight": 500}
        assert style["text"] == P["prose"]
        assert syn["function.definition"] == {"color": P["call"], "font_style": None, "font_weight": 700}
        assert syn["function.macro"]["color"] == P["macro"]
        assert style["warning"] == P["constant"] != syn["function"]["color"]
    dark, light = (t["style"] for t in family["themes"])
    assert dark["editor.background"] == "#131415"
    assert light["editor.background"] == "#FFFDFC"  # the website's page colour
    # panels sit below the editor in both: deeper than the ink, greyer than the paper
    for style in (dark, light):
        assert build.hex_to_oklch(style["panel.background"])[0] < build.hex_to_oklch(style["editor.background"])[0]
    # on paper the bright ANSI variants are the vivid versions of the base hues,
    # not lighter ones: AA caps their lightness, so the punch comes from chroma
    for name in ("red", "green", "blue", "magenta", "cyan"):
        base = build.hex_to_oklch(light[f"terminal.ansi.{name}"])
        bright = build.hex_to_oklch(light[f"terminal.ansi.bright_{name}"])
        assert abs(bright[0] - base[0]) <= 0.02
        assert build.oklab_distance(light[f"terminal.ansi.{name}"], light[f"terminal.ansi.bright_{name}"]) >= 0.03


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
    # text on panels and in the terminal is checked against the surface it sits on,
    # not just the editor background: the old light punct passed the editor but not the panel
    assert any(f.startswith("Paper & Ink Light: wcag: text.placeholder")
               for f in broken(["text.placeholder"], "#756F6A", theme=1))
    assert any(f.startswith("Paper & Ink Dark: wcag: terminal.dim_foreground")
               for f in broken(["terminal.dim_foreground"], build.oklch_to_hex(0.40, 0.008, 65)))
    # ANSI colours in their text roles are held to AA on the terminal background,
    # and the dim variants and the dark grey to the de-emphasis floor
    assert any(f.startswith("Paper & Ink Light: wcag: terminal.ansi.bright_red")
               for f in broken(["terminal.ansi.bright_red"], "#D9553F", theme=1))
    assert any(f.startswith("Paper & Ink Dark: wcag: terminal.ansi.bright_black")
               for f in broken(["terminal.ansi.bright_black"], "#585552"))
    assert any(f.startswith("Paper & Ink Light: wcag: terminal.ansi.dim_green")
               for f in broken(["terminal.ansi.dim_green"], build.oklch_to_hex(0.75, 0.01, 60), theme=1))
    # statuses and placeholder text must clear hovered rows, not just the panel
    assert any(f.startswith("Paper & Ink Dark: wcag: text.placeholder")
               for f in broken(["text.placeholder"], "#908B86"))
    assert any(f.startswith("Paper & Ink Light: wcag: warning")
               for f in broken(["warning"], "#B15602", theme=1))
    # line numbers sit on the highlighted line too
    assert any("line_number" in f and "highlighted" in f
               for f in broken(["editor.line_number"], "#87827D", theme=1))
    # reading text keeps AA under the persistent washes and stays findable under
    # the active match: a full-opacity wash drowns it
    assert any(f.startswith("Paper & Ink Dark: wash: ")
               for f in broken(["search.active_match_background"], "#F5A75E"))
    assert any(f.startswith("Paper & Ink Light: wash: ")
               for f in broken(["search.match_background"], "#A94E03", theme=1))
    family = build.build_family()
    del family["themes"][1]["style"]["editor.indent_guide"]
    assert "Paper & Ink Light: missing key: editor.indent_guide" in build.check(family, SCHEMA)
    assert any(f.startswith("schema") for f in broken(["syntax", "comment", "font_weight"], 450))
    # the checks must not mutate the family they inspect
    family = build.build_family()
    snapshot = copy.deepcopy(family)
    build.check(family, SCHEMA)
    assert family == snapshot


def test_quarto_outputs():
    PL, PD = build.hexes(build.LIGHT), build.hexes(build.DARK)
    light = build.quarto_theme(build.LIGHT, "#FFEEE2")
    dark = build.quarto_theme(build.DARK, "#191B1D")
    # every class Quarto's highlighter puts on a span gets a colour
    assert len(build.KDE_ROLES) == 31 and set(light["text-styles"]) == set(build.KDE_ROLES)
    # comments and docstrings are the prose, in italic, as in Zed
    assert light["text-styles"]["Comment"] == {"text-color": PL["prose"], "selected-text-color": PL["prose"], "italic": True}
    assert dark["text-styles"]["Documentation"]["text-color"] == PD["prose"]
    assert "italic" not in light["text-styles"]["Keyword"]
    # built-ins are the only calls Quarto marks; True/None/self arrive as Variable
    assert light["text-styles"]["BuiltIn"]["text-color"] == PL["call"]
    assert light["text-styles"]["Variable"]["text-color"] == PL["constant"]
    assert dark["editor-colors"]["BackgroundColor"] == "#191B1D"
    # deck line numbers: without this Quarto leaves them in the link colour
    assert light["editor-colors"]["LineNumbers"] == PL["line_number"]
    assert dark["editor-colors"]["LineNumbers"] == PD["line_number"]
    site = build.site_colours()
    assert site["light"]["code_surface"] == "#FFEEE2"
    assert site["dark"]["code_surface"] == build.shade(build.DARK, "active_line") == "#191B1D"
    assert site["dark"]["ground"] == "#131415"
    assert site["dark"]["text"] == "#E0DAD2"
    assert site["dark"]["border"] == "#212223"
    scss = build.site_scss()
    assert "$pi-dark-code-surface: #191B1D !default;" in scss
    assert "$pi-light-string: #157171 !default;" in scss


def test_site_checks():
    assert build.site_check(build.site_colours()) == []
    # a grey wash under light code: the syntax colours drop below AA
    site = build.site_colours()
    site["light"]["code_surface"] = "#C9C1BB"
    assert any(f.startswith("site light: ") for f in build.site_check(site))
    # dark muted text too close to the ground
    site = build.site_colours()
    site["dark"]["muted"] = "#5A5550"
    assert any(f.startswith("site dark: muted") for f in build.site_check(site))


def test_site_line_numbers():
    site = build.site_colours()
    assert site["light"]["line_number"] == "#65696E" and site["dark"]["line_number"] == "#8E8883"
    assert "$pi-dark-line-number: #8E8883 !default;" in build.site_scss()
    # the grey of the line numbers is held to AA on each code surface
    for mode, surface in (("light", "#B9B0A8"), ("dark", "#5A5550")):
        broken = build.site_colours()
        broken[mode]["code_surface"] = surface
        assert any(f.startswith(f"site {mode}: line_number") for f in build.site_check(broken))


def test_site_ansi():
    site = build.site_colours()
    for mode, theme in (("light", build.LIGHT), ("dark", build.DARK)):
        style = build.ui(theme)
        for hue in build.ANSI_HUES:
            assert site[mode][f"ansi_{hue}"] == style[f"terminal.ansi.{hue}"]
            assert site[mode][f"ansi_bright_{hue}"] == style[f"terminal.ansi.bright_{hue}"]
        assert site[mode]["ansi_bright_black"] == build.hexes(theme)["muted"]
    assert site["light"]["ground"] == "#FFFDFC"
    assert "$pi-dark-ansi-yellow: #F5A75E !default;" in build.site_scss()
    # Quarto's notebook yellow on the light page: 1.9:1
    broken = build.site_colours()
    broken["light"]["ansi_yellow"] = "#DDB62B"
    assert any(f.startswith("site light: ansi_yellow") for f in build.site_check(broken))


def test_site_code_bar():
    # the dark code bar is the light bar's rose (#EBADAD, hue 18.8) at L 0.66: visible, 5.7:1
    assert build.site_colours()["dark"]["code_bar"] == "#C17D7E"
    # a bar is a visible boundary, held to WCAG's 3:1 for graphics; the first one was 2.5:1
    broken = build.site_colours()
    broken["dark"]["code_bar"] = "#6E4F4F"
    assert any(f.startswith("site dark: code_bar") for f in build.site_check(broken))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all checks pass")
