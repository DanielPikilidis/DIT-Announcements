"""
Generates assets/category_emojis/dit_cat_<colour>.png, one filled circle per website category colour.
The bot uploads these as application emojis at startup. Run it again after changing src/categories.py:

    pip install pillow
    python3 scripts/make_category_emojis.py

Pillow is only needed here, not by the bot.
"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from categories import CATEGORY_COLOURS, emoji_name

SIZE = 128      # Discord shows emojis at most 128x128
SCALE = 4       # Draw bigger and scale down for smooth edges

def make_circle(colour: int) -> Image.Image:
    big = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    rgb = ((colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF, 255)
    margin = 8 * SCALE
    ImageDraw.Draw(big).ellipse((margin, margin, SIZE * SCALE - margin, SIZE * SCALE - margin), fill=rgb)
    return big.resize((SIZE, SIZE), Image.LANCZOS)

if __name__ == "__main__":
    out = ROOT / "assets" / "category_emojis"
    out.mkdir(parents=True, exist_ok=True)
    for colour in sorted(set(CATEGORY_COLOURS.values())):
        path = out / f"{emoji_name(colour)}.png"
        make_circle(colour).save(path, optimize=True)
        print(path.relative_to(ROOT))
