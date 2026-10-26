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
QUARTO = ROOT / "quarto"


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


def wcag(a, b):
    """WCAG 2 contrast ratio of two colours (1 to 21)."""
    def lum(hex_):
        r, g, b_ = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in _rgb(hex_))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, bg):
    """An #RRGGBBAA colour composited over an opaque background, as the GPU does it."""
    f, b = fg.lstrip("#"), bg.lstrip("#")
    a = int(f[6:8], 16) / 255 if len(f) == 8 else 1.0
    return "#" + "".join(
        f"{round(int(f[i:i + 2], 16) * a + int(b[i:i + 2], 16) * (1 - a)):02X}" for i in (0, 2, 4))


# ---- the two themes: every colour as OKLCH (L, C, h) ----

DARK = {
    "name": "Paper & Ink Dark", "appearance": "dark",
    "ground": (0.19, 0.003, 250),  # "Deep ink", neutral with a hint of cool
    "palette": {
        # text, brightest first
        "prose": (0.94, 0.018, 75),  # all comments and markdown: the page text, in italic
        "code": (0.855, 0.008, 75),  # plain code, a clear step below the prose
        "muted": (0.72, 0.010, 70),
        "punct": (0.66, 0.010, 70),  # AA on the lightest surface it sits on: a hovered row
        "line_number": (0.63, 0.010, 65),  # WCAG AA 4.5:1 on the highlighted line
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
    # UI surfaces as (lightness, chroma) offsets from the ground: panels sit deep,
    # the rest lifts. Chrome sinks well below the page so the editor, active tab and
    # toolbar read as lit paper over the receding docks. The agent panel cannot be
    # separated further: Zed has no agent-specific theme tokens (zed#59171), its
    # backdrop shares panel.background with the docks, and its message cards are
    # editor.background at ~20% opacity, which flattens into the chrome at this
    # depth. title_inactive, border and dim_black keep their old panel distances.
    "shades": {
        "panel": (-0.055, 0), "title_inactive": (-0.07, 0), "border": (-0.085, 0), "border_variant": (0.06, 0),
        "raised": (0.05, 0.002), "hover": (0.085, 0.004), "active_line": (0.03, 0.002),
        "highlighted_line": (0.045, 0.002), "wrap": (0.05, 0), "wrap_active": (0.12, 0), "invisible": (0.15, 0),
        "indent": (0.07, 0), "indent_active": (0.17, 0), "indent_hover": (0.22, 0),
        "black": (0.05, 0), "bright_black": (0.32, 0), "dim_black": (-0.055, 0),
    },
    "selected": (0.12, 0.029, 235),  # offset from the ground, with its own hue
    # alpha suffixes of the tinted washes; reading text keeps AA on the composite
    "washes": {"match": "40", "active_match": "66", "doc_read": "22", "doc_write": "33"},
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
        # text, darkest first: slate ink, the websites' #363D45 family
        "prose": (0.27, 0.015, 252),  # the darkest text, in italic
        "code": (0.42, 0.012, 252),
        "muted": (0.50, 0.010, 252),
        "punct": (0.509, 0.009, 252),  # AA on the darkest surface it sits on: a hovered row
        "line_number": (0.52, 0.009, 252),  # WCAG AA on the highlighted line
        "disabled": (0.72, 0.008, 252),
        # the dark theme's hues, darkened for paper, a touch crisper for clarity
        "call": (0.474, 0.125, 80),  # ochre, kept clear of the darker orange
        "string": (0.500, 0.080, 195),  # teal, the websites' accent family
        "constant": (0.522, 0.155, 50),  # orange, AA on panels and hovered rows too
        "keyword": (0.50, 0.115, 245),  # blue, the websites' accent family
        "macro": (0.52, 0.160, 8),  # rose, apart from the error red
        "violet": (0.50, 0.100, 300),
        "error": (0.45, 0.165, 25),  # the websites' brick red #9E2B2B, deepened
        "selection": (0.62, 0.060, 240),
    },
    # cool slate ink on warm paper: the surfaces step darker in the paper's own
    # warm hue, and the warmth lives in the washes — the active line is the
    # tutorials' peach code-line highlight
    # Later, maybe: active_line exactly the sites' codeline #FFEEE2, so a theme
    # user's current line and the sites' light code blocks are one colour. Kept
    # paler for now (2026-10-26): a calmer band under the cursor. If it moves,
    # highlighted_line has to step further out to stay distinct from it.
    "shades": {
        "panel": (-0.05, 0.004), "title_inactive": (-0.065, 0.004), "border": (-0.125, 0.004),
        "border_variant": (-0.07, 0.004), "raised": (0, 0), "hover": (-0.075, 0.004),
        "active_line": (-0.030, 0.0095), "highlighted_line": (-0.040, 0.0155), "wrap": (-0.06, 0.003),
        "wrap_active": (-0.14, 0.004), "invisible": (-0.22, 0.004), "indent": (-0.08, 0.003),
        "indent_active": (-0.18, 0.004), "indent_hover": (-0.24, 0.004),
    },
    "selected": (-0.10, 0.03, 240),
    "washes": {"match": "1F", "active_match": "55", "doc_read": "16", "doc_write": "1F"},
    # on paper, brightness reads as saturation: the bright variants are the vivid
    # versions of the base hues, not the lighter ones
    "ansi": {
        "black": ((0.35, 0.010, 252), (0.52, 0.009, 252), (0.45, 0.010, 252)),
        "red": ("error", (0.46, 0.21, 12), (0.45, 0.15, 32)),
        "green": ("string", (0.514, 0.13, 165), (0.42, 0.05, 195)),
        "yellow": ("constant", "call", (0.48, 0.12, 55)),
        "blue": ("keyword", (0.515, 0.14, 255), (0.42, 0.08, 245)),
        "magenta": ("violet", (0.52, 0.16, 315), (0.42, 0.08, 300)),
        "cyan": ((0.52, 0.07, 215), (0.52, 0.125, 195), (0.45, 0.05, 215)),
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
    w = theme["washes"]
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
        "search.match_background": p["constant"] + w["match"],
        "search.active_match_background": p["constant"] + w["active_match"],
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
        "editor.document_highlight.read_background": p["keyword"] + w["doc_read"],
        "editor.document_highlight.write_background": p["keyword"] + w["doc_write"],
        "editor.document_highlight.bracket_background": p["keyword"] + w["doc_write"],
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
        return {"color": p[role], "font_style": None, "font_weight": 500, **extra}  # 500: the code reads slightly heavier than the default 400
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


# ---- the course sites (Lecture-Foundations syncs quarto/ to every site) ----

# The classes Quarto's highlighter (KDE syntax definitions) puts on code spans,
# each mapped to a palette role. Coarser than Zed's tree-sitter: only built-ins
# are calls, so user functions and constructors stay plain on the sites.
KDE_ROLES = {
    "Comment": "prose", "Documentation": "prose", "Annotation": "prose", "CommentVar": "prose",
    "Information": "prose", "RegionMarker": "prose",
    "Normal": "code", "Operator": "code", "Others": "code",
    "Keyword": "keyword", "ControlFlow": "keyword", "Import": "keyword", "DataType": "keyword",
    "Extension": "keyword",
    "BuiltIn": "call", "Function": "call",
    "String": "string", "SpecialString": "string", "VerbatimString": "string", "Char": "string",
    "DecVal": "constant", "Float": "constant", "BaseN": "constant", "Constant": "constant",
    "Variable": "constant", "SpecialChar": "constant", "Warning": "constant",
    "Attribute": "macro", "Preprocessor": "macro",
    "Error": "error", "Alert": "error",
}


ANSI_HUES = ("red", "green", "yellow", "blue", "magenta", "cyan")


def site_colours():
    """Every colour the sites take from Paper & Ink besides the syntax, per mode."""
    d, l = hexes(DARK), hexes(LIGHT)
    site = {
        # the sites' peach codeline, kept (2026-10-26); see the active_line note in LIGHT
        "light": {"ground": oklch_to_hex(*LIGHT["ground"]), "code_surface": "#FFEEE2", "string": l["string"]},
        "dark": {
            "ground": oklch_to_hex(*DARK["ground"]),
            "text": oklch_to_hex(0.89, 0.013, 75),  # between the code and the prose
            "heading": d["prose"], "muted": d["muted"], "border": shade(DARK, "border_variant"),
            "code_surface": shade(DARK, "active_line"),  # code blocks look like the editor
            "string": d["string"], "code_bar": oklch_to_hex(0.66, 0.085, 18),  # the light bar's rose, lifted for the dark ground,
        },
    }
    for theme, mode in ((LIGHT, "light"), (DARK, "dark")):
        style = ui(theme)
        for hue in ANSI_HUES:
            site[mode][f"ansi_{hue}"] = style[f"terminal.ansi.{hue}"]
            site[mode][f"ansi_bright_{hue}"] = style[f"terminal.ansi.bright_{hue}"]
        # the grey Julia prints for de-emphasis; the terminal's own bright black is only held to 3:1
        site[mode]["ansi_bright_black"] = hexes(theme)["muted"]
        site[mode]["line_number"] = hexes(theme)["line_number"]  # Quarto ignores the theme's LineNumbers; the core styles it
    return site


def quarto_theme(theme, surface):
    """A KDE highlight theme, the format Quarto's `syntax-highlighting` reads."""
    p = hexes(theme)
    styles = {}
    for cls, role in KDE_ROLES.items():
        styles[cls] = {"text-color": p[role], "selected-text-color": p[role]}
        if role == "prose":
            styles[cls]["italic"] = True
    return {"metadata": {"name": theme["name"], "revision": 1, "license": "MIT"},
            "text-styles": styles, "editor-colors": {"BackgroundColor": surface, "LineNumbers": p["line_number"]}}


def site_scss():
    """SCSS variables for the sites, all !default so one site can still override one."""
    lines = ["// Generated by paper-and-ink-theme/build.py. Change build.py and rebuild."]
    for mode, colours in site_colours().items():
        lines += [f"$pi-{mode}-{name.replace('_', '-')}: {value} !default;" for name, value in colours.items()]
    return "\n".join(lines) + "\n"


def site_check(site):
    """Failed checks for the sites: code on each code surface, the dark page text on its ground."""
    failures = []
    for theme, mode in ((LIGHT, "light"), (DARK, "dark")):
        p, surface = hexes(theme), site[mode]["code_surface"]
        for role in READING + ("error",):
            ratio = wcag(p[role], surface)
            if ratio < 4.5:
                failures.append(f"site {mode}: {role} {p[role]} on code surface {surface} is {ratio:.2f}:1, needs 4.5:1")
    for mode in ("light", "dark"):
        for name, value in site[mode].items():
            if name != "line_number" and not name.startswith("ansi_"):
                continue
            for surface_name in ("ground", "code_surface"):
                surface = site[mode][surface_name]
                ratio = wcag(value, surface)
                if ratio < 4.5:
                    failures.append(f"site {mode}: {name} {value} on {surface_name} {surface} is {ratio:.2f}:1, needs 4.5:1")
    bar = wcag(site["dark"]["code_bar"], site["dark"]["ground"])
    if bar < 3.0:
        failures.append(f"site dark: code_bar {site['dark']['code_bar']} on {site['dark']['ground']} is {bar:.2f}:1, needs 3:1")
    dark = site["dark"]
    for name in ("text", "heading", "muted"):
        ratio = wcag(dark[name], dark["ground"])
        if ratio < 4.5:
            failures.append(f"site dark: {name} {dark[name]} on {dark['ground']} is {ratio:.2f}:1, needs 4.5:1")
    return failures


# ---- checks ----

# Contrast floors (APCA Lc), checked on the editor's line surfaces. Every
# checked role must also reach WCAG 2 AA, 4.5:1, on all of them.
FLOORS = {"prose": 75, "code": 75, "call": 55, "string": 55, "constant": 55, "keyword": 55, "macro": 55,
          "error": 45, "punct": 35, "line_number": 30}
LINE_SURFACES = ("editor.background", "editor.active_line.background", "editor.highlighted_line.background")
# Text and status markers that sit on panels, popovers and hovered rows
PANEL_TEXT = ("text", "text.muted", "text.placeholder", "text.accent", "icon", "icon.muted",
              "icon.placeholder", "icon.accent", "link_text.hover", "conflict", "created", "deleted",
              "error", "hidden", "hint", "ignored", "info", "modified", "predictive", "renamed",
              "success", "unreachable", "warning")
PANEL_SURFACES = ("panel.background", "elevated_surface.background", "element.hover")
# Reading roles under the tinted washes. Error and punctuation, the de-emphasis
# pair, are allowed to fade under a wash: they are not reading text.
READING = ("prose", "code", "call", "string", "constant", "keyword", "macro")
# Persistent washes hold AA for reading text; the active search match is a
# transient highlight, like selection, and only needs to stay findable.
WASHES = (("search.match_background", 4.5), ("editor.document_highlight.read_background", 4.5),
          ("editor.document_highlight.write_background", 4.5),
          ("editor.document_highlight.bracket_background", 4.5), ("search.active_match_background", 3.0))
# The de-emphasis floor, for what is meant to sit visibly below the text
DE_EMPHASIS = 3.0
# Keys Zed's own One Dark sets that schema v0.2.0 does not list yet
NEWER_KEYS = ["search.active_match_background", "editor.hover_line_number", "version_control.added",
              "version_control.modified", "version_control.deleted", "version_control.word_added",
              "version_control.word_deleted", "version_control.conflict_marker.ours",
              "version_control.conflict_marker.theirs"]


def ansi_checks(theme):
    """(key, WCAG floor) for every ANSI colour a program can print as text.

    The family that mirrors the background (black in the dark theme, white in
    the light one) is a fill colour, except dark bright black: the conventional
    de-emphasized grey. Dim variants de-emphasize on purpose, so they only need
    the de-emphasis floor.
    """
    dark = theme["appearance"] == "dark"
    bg_family = "black" if dark else "white"
    checks = [("terminal.ansi.bright_black", DE_EMPHASIS)] if dark else []
    for name in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"):
        if name != bg_family:
            checks += [(f"terminal.ansi.{name}", 4.5), (f"terminal.ansi.bright_{name}", 4.5),
                       (f"terminal.ansi.dim_{name}", DE_EMPHASIS)]
    return checks


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
        for bg_key in LINE_SURFACES:
            for role, floor in FLOORS.items():
                lc = apca(c[role], style[bg_key])
                if lc < floor:
                    failures.append(f"{name}: contrast: {role} {c[role]} on {bg_key} is Lc {lc:.1f}, needs {floor}")
                ratio = wcag(c[role], style[bg_key])
                if ratio < 4.5:
                    failures.append(f"{name}: wcag: {role} {c[role]} on {bg_key} is {ratio:.2f}:1, needs 4.5:1")
            ratio = wcag(style["editor.hover_line_number"], style[bg_key])
            if ratio < 4.5:
                failures.append(f"{name}: wcag: hover_line_number on {bg_key} is {ratio:.2f}:1, needs 4.5:1")
        for key in PANEL_TEXT:
            for bg_key in PANEL_SURFACES:
                ratio = wcag(style[key], style[bg_key])
                if ratio < 4.5:
                    failures.append(f"{name}: wcag: {key} {style[key]} on {bg_key} is {ratio:.2f}:1, needs 4.5:1")
        for key in ("terminal.foreground", "terminal.bright_foreground", "terminal.dim_foreground"):
            ratio = wcag(style[key], style["terminal.background"])
            if ratio < 4.5:
                failures.append(f"{name}: wcag: {key} on terminal.background is {ratio:.2f}:1, needs 4.5:1")
        for key, floor in ansi_checks(theme):
            ratio = wcag(style[key], style["terminal.background"])
            if ratio < floor:
                failures.append(f"{name}: wcag: {key} {style[key]} on terminal.background is {ratio:.2f}:1, needs {floor}:1")
        for key, floor in WASHES:
            composite = blend(style[key], style["editor.background"])
            for role in READING:
                ratio = wcag(c[role], composite)
                if ratio < floor:
                    failures.append(f"{name}: wash: {role} on {key} {style[key]} ({composite}) is {ratio:.2f}:1, needs {floor}:1")
        for a, b, need in (("prose", "code", 0.05), ("call", "constant", 0.08), ("error", "macro", 0.08)):
            d = oklab_distance(c[a], c[b])
            if d < need:
                failures.append(f"{name}: {a} and {b} only {d:.3f} apart in OKLab, need {need}")
    return failures


def main():
    family, site = build_family(), site_colours()
    failures = check(family, json.loads(SCHEMA.read_text())) + site_check(site)
    OUT.write_text(json.dumps(family, indent=2) + "\n")
    QUARTO.mkdir(exist_ok=True)
    for theme, mode in ((LIGHT, "light"), (DARK, "dark")):
        theme_json = quarto_theme(theme, site[mode]["code_surface"])
        (QUARTO / f"_paper-and-ink-{mode}.theme").write_text(json.dumps(theme_json, indent=2) + "\n")
    (QUARTO / "_paper-and-ink.scss").write_text(site_scss())
    print(f"wrote {OUT.relative_to(ROOT)} and {QUARTO.relative_to(ROOT)}/")
    for f in failures:
        print("FAIL", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
