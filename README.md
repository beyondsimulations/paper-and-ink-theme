# Paper & Ink

A dark and a light [Zed](https://zed.dev) theme for files that are mostly text:
the comments read like the page, the code sits underneath in soft colours.
**Paper & Ink Dark** puts paper-white comments on deep ink; **Paper & Ink Light**
puts ink comments on paper.

![Paper & Ink with a Julia tutorial](screenshot.png)

Most themes grey out comments. In tutorials and notebooks in percent format
(`# %%` cells), the comments are the instructions, so Paper & Ink gives them the
strongest contrast on screen, sets them in italic and gives the code fewer,
calmer colours.

## Install

Open the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` elsewhere),
choose **zed: extensions**, search for "Paper & Ink" and install it. Then pick
**Paper & Ink Dark** or **Paper & Ink Light** with **theme selector: toggle**.
To follow your system's light and dark mode, put this in your settings
(**zed: open settings file**):

```json
"theme": { "mode": "system", "light": "Paper & Ink Light", "dark": "Paper & Ink Dark" }
```

## Colours

Every colour is defined once in `build.py` as OKLCH. Contrast follows APCA:
comments Lc 94 (dark) and 97 (light), plain code Lc 76 and 84, every syntax
colour at least Lc 55.

| Role | Dark | Light |
|---|---|---|
| Comments (italic), markdown text | `#F2EADE` | `#2E241D` |
| Plain code | `#D1CDC8` | `#524C47` |
| Function calls (bold where defined) | `#EED284` | `#886108` |
| Strings | `#97CDCC` | `#327272` |
| Numbers, constants | `#F5A75E` | `#BC5B03` |
| Keywords, types | `#7ABAE0` | `#2E6896` |
| Macros, decorators | `#F3928F` | `#A83F59` |
| Background | `#161311` | `#FFFDFC` |

## Rebuild

`uv run build.py` writes `themes/paper-and-ink.json` and fails if a colour drops
below its contrast floor. `uv run test_build.py` checks the colour maths.

## License

MIT
