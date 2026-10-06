"""Turn logo SVGs into small pixel-art sprites stored in scripts/icons.json.

Local-only helper (needs Pillow and rsvg-convert); build.py reads the JSON and stays stdlib-only.
Usage: python3 scripts/pixelate_icons.py <dir-with-svgs> name=file.svg [name=file.svg ...]
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

SIZE = 16
MAX_COLORS = 5
MIN_LUMA = 70  # lift near-black so the sprite stays visible on the dark slots
ICONS_JSON = Path(__file__).with_name("icons.json")


def rasterize(svg: Path) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        subprocess.run(
            ["rsvg-convert", "-w", "256", "-h", "256", "--keep-aspect-ratio", str(svg), "-o", tmp.name],
            check=True,
        )
        img = Image.open(tmp.name).convert("RGBA")
        img.load()
    bbox = img.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()
    img = img.crop(bbox)
    side = max(img.size)
    square = Image.new("RGBA", (side, side))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return square


def lift(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    luma = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    if luma >= MIN_LUMA:
        return rgb
    return tuple(min(255, c + int(MIN_LUMA - luma)) for c in rgb)


def pixelate(svg: Path) -> dict:
    small = rasterize(svg).resize((SIZE, SIZE), Image.Resampling.BOX)
    opaque = small.getchannel("A").point(lambda a: 255 if a >= 110 else 0)
    flat = Image.new("RGB", small.size, (0, 0, 0))
    flat.paste(small.convert("RGB"), mask=opaque)
    quant = flat.quantize(colors=MAX_COLORS + 1, method=Image.Quantize.MEDIANCUT)
    raw_palette = quant.getpalette()

    palette: list[str] = []
    index_of: dict[int, str] = {}
    rows = []
    for y in range(SIZE):
        row = ""
        for x in range(SIZE):
            if not opaque.getpixel((x, y)):
                row += "."
                continue
            q = quant.getpixel((x, y))
            if q not in index_of:
                rgb = lift(tuple(raw_palette[q * 3 : q * 3 + 3]))
                palette.append("#%02x%02x%02x" % rgb)
                index_of[q] = str(len(palette) - 1)
            row += index_of[q]
        rows.append(row)
    return {"palette": palette, "rows": rows}


def main() -> None:
    src = Path(sys.argv[1])
    icons = json.loads(ICONS_JSON.read_text()) if ICONS_JSON.exists() else {}
    for pair in sys.argv[2:]:
        name, file = pair.split("=", 1)
        icons[name] = pixelate(src / file)
    ICONS_JSON.write_text(json.dumps(icons, indent=1) + "\n")


if __name__ == "__main__":
    main()
