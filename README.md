# Paper & Ink

A dark [Zed](https://zed.dev) theme for files that are mostly text: paper-white
comments on a deep ink ground, with soft code colours underneath.

![Paper & Ink with a Julia tutorial](screenshot.png)

Most dark themes grey out comments. In tutorials and notebooks in percent format
(`# %%` cells), the comments are the instructions, so Paper & Ink makes them the
brightest text on screen and gives the code fewer, calmer colours.

## Install

Open the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` elsewhere),
choose **zed: extensions**, search for "Paper & Ink" and install it. Then pick
it with **theme selector: toggle**.

## Colours

Every colour is defined once in `build.py` as OKLCH. Contrast follows APCA:
comments Lc 86, plain code Lc 76, every syntax colour at least Lc 55.

| Role | Colour |
|---|---|
| Comments, markdown text | `#EADCC9` |
| Plain code | `#D1CDC8` |
| Function calls (bold where defined) | `#EED284` |
| Strings | `#77D4CE` |
| Numbers, constants | `#F5A75E` |
| Keywords, types | `#7ABAE0` |
| Macros, decorators | `#F3928F` |
| Background | `#161311` |

## Rebuild

`uv run build.py` writes `themes/paper-and-ink.json` and fails if a colour drops
below its contrast floor. `uv run test_build.py` checks the colour maths.

## License

MIT
