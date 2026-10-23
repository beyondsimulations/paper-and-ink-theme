# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4"]
# ///
"""Build themes/paper-and-ink.json (a dark and a light theme) from the OKLCH palettes below, then check it.

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


# ---- the two themes: every colour as OKLCH (L, C, h) ----

DARK = {
    "name": "Paper & Ink Dark", "appearance": "dark",
    "ground": (0.19, 0.006, 65),  # "Deep ink"
    "palette": {
        # text, brightest first
        "prose": (0.94, 0.018, 75),  # all comments and markdown: the page text, in italic
        "code": (0.85, 0.008, 75),  # plain code, a clear step below the prose
        "muted": (0.72, 0.010, 70),
        "punct": (0.64, 0.010, 70),
        "line_number": (0.58, 0.010, 65),
        "disabled": (0.44, 0.008, 65),
        # syntax hues, lightness stepped by role
        "call": (0.87, 0.102, 90),  # gold
        "string": (0.81, 0.055, 195),  # calmer teal
        "constant": (0.79, 0.128, 62),  # orange
        "keyword": (0.76, 0.085, 235),  # blue
        "macro": (0.76, 0.119, 22),  # coral
        "violet": (0.79, 0.077, 300),
        "error": (0.70, 0.18, 30),  # vermilion, apart from the macro coral
        "selection": (0.55, 0.06, 235),
    },
    # UI surfaces as (lightness, chroma) offsets from the ground: panels sit deeper, the rest lifts
    "shades": {
        "panel": (-0.03, 0), "title_inactive": (-0.045, 0), "border": (-0.06, 0), "border_variant": (0.06, 0),
        "raised": (0.05, 0.002), "hover": (0.085, 0.004), "active_line": (0.03, 0.002),
        "highlighted_line": (0.045, 0.002), "wrap": (0.05, 0), "wrap_active": (0.12, 0), "invisible": (0.15, 0),
        "indent": (0.07, 0), "indent_active": (0.17, 0), "indent_hover": (0.22, 0),
        "black": (0.05, 0), "bright_black": (0.26, 0), "dim_black": (-0.03, 0),
    },
    "selected": (0.12, 0.029, 235),  # offset from the ground, with its own hue
    # terminal: (base, bright, dim), each a palette role, a shade or an OKLCH triple
    "ansi": {
        "black": ("black", "bright_black", "dim_black"),
        "red": ("error", (0.82, 0.11, 30), (0.58, 0.12, 30)),
        "green": ("string", (0.89, 0.07, 190), (0.62, 0.07, 190)),
        "yellow": ("constant", "call", (0.62, 0.10, 62)),
        "blue": ("keyword", (0.86, 0.06, 235), (0.58, 0.07, 235)),
        "magenta": ("violet", (0.88, 0.05, 300), (0.60, 0.06, 300)),
        "cyan": ((0.81, 0.077, 210), (0.89, 0.05, 210), (0.60, 0.06, 210)),
        "white": ("code", "prose", "punct"),
    },
}

LIGHT = {
    "name": "Paper & Ink Light", "appearance": "light",
    "ground": hex_to_oklch("#FFFDFC"),  # the website's page colour
    "palette": {
        # text, darkest first: ink on paper
        "prose": (0.27, 0.020, 55),  # the darkest text, in italic
        "code": (0.42, 0.012, 60),
        "muted": (0.50, 0.010, 60),
        "punct": (0.58, 0.010, 60),
        "line_number": (0.66, 0.010, 60),
        "disabled": (0.72, 0.008, 60),
        # the dark theme's hues, darkened for paper
        "call": (0.52, 0.105, 80),  # ochre
        "string": (0.51, 0.065, 195),  # teal
        "constant": (0.58, 0.150, 52),  # orange
        "keyword": (0.50, 0.095, 245),  # blue
        "macro": (0.52, 0.140, 8),  # rose, apart from the error red
        "violet": (0.50, 0.100, 300),
        "error": (0.55, 0.200, 32),
        "selection": (0.62, 0.060, 240),
    },
    # on paper every surface steps darker, slightly warm; popovers stay paper-white
    "shades": {
        "panel": (-0.035, 0.004), "title_inactive": (-0.05, 0.004), "border": (-0.11, 0.004),
        "border_variant": (-0.07, 0.004), "raised": (0, 0), "hover": (-0.06, 0.004),
        "active_line": (-0.02, 0.003), "highlighted_line": (-0.03, 0.003), "wrap": (-0.06, 0.003),
        "wrap_active": (-0.14, 0.004), "invisible": (-0.22, 0.004), "indent": (-0.08, 0.003),
        "indent_active": (-0.18, 0.004), "indent_hover": (-0.24, 0.004),
    },
    "selected": (-0.10, 0.03, 240),
    "ansi": {
        "black": ((0.35, 0.010, 60), (0.55, 0.010, 60), (0.45, 0.010, 60)),
        "red": ("error", (0.62, 0.17, 32), (0.45, 0.15, 32)),
        "green": ("string", (0.60, 0.07, 195), (0.42, 0.05, 195)),
        "yellow": ("constant", "call", (0.48, 0.12, 55)),
        "blue": ("keyword", (0.60, 0.09, 245), (0.42, 0.08, 245)),
        "magenta": ("violet", (0.60, 0.09, 300), (0.42, 0.08, 300)),
        "cyan": ((0.55, 0.07, 215), (0.63, 0.06, 215), (0.45, 0.05, 215)),
        "white": ((0.85, 0.008, 60), (0.95, 0.005, 60), (0.75, 0.008, 60)),
    },
}

THEMES = [DARK, LIGHT]


def hexes(theme):
    return {role: oklch_to_hex(*v) for role, v in theme["palette"].items()}


def shade(theme, name):
    """The ground moved by the theme's (lightness, chroma) offset for one UI surface."""
    L, C, h = theme["ground"]
    dl, dc = theme["shades"][name]
    return oklch_to_hex(L + dl, C + dc, h)


CLEAR = "#00000000"


def ui(theme):
    p = hexes(theme)
    sh = lambda name: shade(theme, name)
    L, C, _ = theme["ground"]
    dl, dc, hue = theme["selected"]
    editor, panel, raised, hover = oklch_to_hex(*theme["ground"]), sh("panel"), sh("raised"), sh("hover")
    selected = oklch_to_hex(L + dl, C + dc, hue)
    style = {
        "background.appearance": "opaque",
        "accents": [p["keyword"], p["call"], p["string"], p["macro"], p["violet"], p["constant"]],
        "border": sh("border"), "border.variant": sh("border_variant"), "border.focused": p["keyword"] + "99",
        "border.selected": p["keyword"] + "66", "border.transparent": CLEAR, "border.disabled": sh("border_variant"),
        "elevated_surface.background": raised, "surface.background": panel, "background": panel,
        "element.background": raised, "element.hover": hover, "element.active": selected,
        "element.selected": selected, "element.disabled": raised, "drop_target.background": p["keyword"] + "33",
        "ghost_element.background": CLEAR, "ghost_element.hover": hover, "ghost_element.active": selected,
        "ghost_element.selected": selected, "ghost_element.disabled": CLEAR,
        "text": p["prose"], "text.muted": p["muted"], "text.placeholder": p["punct"],
        "text.disabled": p["disabled"], "text.accent": p["constant"],
        "icon": p["code"], "icon.muted": p["muted"], "icon.disabled": p["disabled"],
        "icon.placeholder": p["punct"], "icon.accent": p["constant"],
        "status_bar.background": panel, "title_bar.background": panel,
        "title_bar.inactive_background": sh("title_inactive"),
        "toolbar.background": editor, "tab_bar.background": panel, "tab.inactive_background": panel,
        "tab.active_background": editor,
        "search.match_background": p["constant"] + "40", "search.active_match_background": p["constant"] + "73",
        "panel.background": panel, "panel.focused_border": p["keyword"] + "99",
        "panel.indent_guide": sh("indent"), "panel.indent_guide_active": sh("indent_active"),
        "panel.indent_guide_hover": sh("indent_hover"), "pane.focused_border": p["keyword"] + "99",
        "pane_group.border": sh("border"),
        "scrollbar.thumb.background": p["code"] + "20", "scrollbar.thumb.hover_background": p["code"] + "38",
        "scrollbar.thumb.border": CLEAR, "scrollbar.track.background": CLEAR, "scrollbar.track.border": CLEAR,
        "editor.foreground": p["code"], "editor.background": editor, "editor.gutter.background": editor,
        "editor.subheader.background": panel, "editor.active_line.background": sh("active_line"),
        "editor.highlighted_line.background": sh("highlighted_line"), "editor.line_number": p["line_number"],
        "editor.active_line_number": p["code"], "editor.hover_line_number": p["muted"],
        "editor.invisible": sh("invisible"), "editor.wrap_guide": sh("wrap"),
        "editor.active_wrap_guide": sh("wrap_active"),
        "editor.indent_guide": sh("indent"), "editor.indent_guide_active": sh("indent_active"),
        "editor.document_highlight.read_background": p["keyword"] + "22",
        "editor.document_highlight.write_background": p["keyword"] + "33",
        "editor.document_highlight.bracket_background": p["keyword"] + "33",
        "terminal.background": panel, "terminal.ansi.background": panel, "terminal.foreground": p["code"],
        "terminal.bright_foreground": p["prose"], "terminal.dim_foreground": p["punct"],
        "link_text.hover": p["constant"],
        "version_control.added": p["string"], "version_control.modified": p["keyword"],
        "version_control.deleted": p["error"], "version_control.word_added": p["string"] + "40",
        "version_control.word_deleted": p["error"] + "40",
        "version_control.conflict_marker.ours": p["string"] + "33",
        "version_control.conflict_marker.theirs": p["keyword"] + "33",
    }

    def colour(ref):
        if isinstance(ref, tuple):
            return oklch_to_hex(*ref)
        return p[ref] if ref in p else sh(ref)

    for name, (base, bright, dim) in theme["ansi"].items():  # the Julia REPL matches the editor
        style[f"terminal.ansi.{name}"] = colour(base)
        style[f"terminal.ansi.bright_{name}"] = colour(bright)
        style[f"terminal.ansi.dim_{name}"] = colour(dim)
    # warnings in orange, not in the call colour: their squiggles sit under calls
    status = {"conflict": "constant", "created": "string", "deleted": "error", "error": "error",
              "hidden": "punct", "hint": "punct", "ignored": "punct", "info": "keyword", "modified": "keyword",
              "predictive": "punct", "renamed": "violet", "success": "string", "unreachable": "punct",
              "warning": "constant"}
    for name, role in status.items():
        style[name], style[f"{name}.background"], style[f"{name}.border"] = p[role], p[role] + "1A", p[role] + "4D"
    return style


def syntax(theme):
    p = hexes(theme)

    def s(role, **extra):
        return {"color": p[role], "font_style": None, "font_weight": None, **extra}
    return {
        # prose: comments are the instructions in the tutorials
        "comment": s("prose", font_style="italic"), "comment.doc": s("prose", font_style="italic"),
        "title": s("prose", font_weight=700), "emphasis": s("prose", font_style="italic"),
        "emphasis.strong": s("prose", font_weight=700),
        # code
        "function": s("call"), "function.definition": s("call", font_weight=700),
        "function.macro": s("macro"), "attribute": s("macro"), "selector.pseudo": s("macro"),
        "string": s("string"), "string.special": s("string"), "text.literal": s("string"),
        "number": s("constant"), "boolean": s("constant"), "constant": s("constant"),
        "constant.builtin": s("constant"), "variable.builtin": s("constant"), "variant": s("constant"),
        "string.escape": s("constant"), "string.regex": s("constant"), "string.special.symbol": s("constant"),
        "punctuation.special": s("constant"), "punctuation.list_marker": s("constant"),
        "keyword": s("keyword"), "type": s("keyword"), "type.builtin": s("keyword"), "constructor": s("keyword"),
        "enum": s("keyword"), "tag": s("keyword"), "selector": s("keyword"), "link_text": s("keyword"),
        "variable": s("code"), "variable.parameter": s("code"), "variable.special": s("code"),
        "variable.member": s("code"), "property": s("code"), "operator": s("code"), "primary": s("code"),
        "namespace": s("code"), "embedded": s("code"),
        "punctuation": s("punct"), "punctuation.bracket": s("punct"), "punctuation.delimiter": s("punct"),
        "punctuation.markup": s("punct"), "link_uri": s("punct"), "hint": s("punct"),
        "label": s("muted"), "preproc": s("muted"), "predictive": s("punct", font_style="italic"),
        "diff.plus": s("string"), "diff.minus": s("error"),
    }


def build_theme(theme):
    p, style = hexes(theme), ui(theme)
    style["players"] = [
        {"cursor": p["constant"], "background": p["constant"], "selection": p["selection"] + "66"},
        {"cursor": p["string"], "background": p["string"], "selection": p["string"] + "33"},
        {"cursor": p["violet"], "background": p["violet"], "selection": p["violet"] + "33"},
        {"cursor": p["macro"], "background": p["macro"], "selection": p["macro"] + "33"},
    ]
    style["syntax"] = syntax(theme)
    return {"name": theme["name"], "appearance": theme["appearance"], "style": style}


def build_family():
    return {
        "$schema": "https://zed.dev/schema/themes/v0.2.0.json",
        "name": "Paper & Ink",
        "author": "Tobias Vlcek",
        "themes": [build_theme(t) for t in THEMES],
    }


# ---- checks ----

# Contrast floors (APCA Lc), checked on the ground and on the active line of each theme
FLOORS = {"prose": 75, "code": 75, "call": 55, "string": 55, "constant": 55, "keyword": 55, "macro": 55,
          "error": 45, "punct": 35, "line_number": 30}
# Keys Zed's own One Dark sets that schema v0.2.0 does not list yet
NEWER_KEYS = ["search.active_match_background", "editor.hover_line_number", "version_control.added",
              "version_control.modified", "version_control.deleted", "version_control.word_added",
              "version_control.word_deleted", "version_control.conflict_marker.ours",
              "version_control.conflict_marker.theirs"]


def shipped_colours(style):
    """The colour of each checked role, read from the generated theme (not from the palette)."""
    syn = style["syntax"]
    return {"prose": syn["comment"]["color"], "code": style["editor.foreground"],
            "call": syn["function"]["color"], "string": syn["string"]["color"],
            "constant": syn["number"]["color"], "keyword": syn["keyword"]["color"],
            "macro": syn["function.macro"]["color"], "error": style["error"],
            "punct": syn["punctuation"]["color"], "line_number": style["editor.line_number"]}


def check(family, schema):
    """List of failed checks, each prefixed with its theme; empty when both themes are fine."""
    import jsonschema

    failures = []
    try:
        jsonschema.validate(family, schema)
    except jsonschema.ValidationError as e:
        failures.append(f"schema: {e.message}")
    wanted = list(schema["definitions"]["ThemeStyleContent"]["properties"]) + NEWER_KEYS
    for theme in family["themes"]:
        style, name = theme["style"], theme["name"]
        failures += [f"{name}: missing key: {k}" for k in wanted if k not in style]
        c = shipped_colours(style)
        for bg_key in ("editor.background", "editor.active_line.background"):
            for role, floor in FLOORS.items():
                lc = apca(c[role], style[bg_key])
                if lc < floor:
                    failures.append(f"{name}: contrast: {role} {c[role]} on {bg_key} is Lc {lc:.1f}, needs {floor}")
        for a, b, need in (("prose", "code", 0.05), ("call", "constant", 0.08), ("error", "macro", 0.08)):
            d = oklab_distance(c[a], c[b])
            if d < need:
                failures.append(f"{name}: {a} and {b} only {d:.3f} apart in OKLab, need {need}")
    return failures


def main():
    family = build_family()
    failures = check(family, json.loads(SCHEMA.read_text()))
    OUT.write_text(json.dumps(family, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for f in failures:
        print("FAIL", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
