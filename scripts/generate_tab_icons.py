"""Create compact, original tab-bar icons for the Mini Program."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parents[1] / "miniprogram" / "assets" / "tabbar"
OUT.mkdir(parents=True, exist_ok=True)
PALETTE = {"default": "#A28691", "active": "#E86990"}

def draw_icon(name, color):
    image = Image.new("RGBA", (81, 81), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = 5
    if name == "home":
        draw.polygon([(14, 38), (40, 15), (67, 38)], outline=color, width=width)
        draw.rounded_rectangle((21, 36, 60, 65), radius=5, outline=color, width=width)
        draw.line((37, 65, 37, 49), fill=color, width=width)
    elif name == "approval":
        draw.rounded_rectangle((19, 14, 62, 67), radius=7, outline=color, width=width)
        draw.line((29, 31, 53, 31), fill=color, width=width)
        draw.line((29, 43, 53, 43), fill=color, width=width)
        draw.line((29, 55, 45, 55), fill=color, width=width)
        draw.line((22, 23, 29, 23), fill=color, width=width)
    else:
        draw.ellipse((27, 14, 54, 41), outline=color, width=width)
        draw.arc((17, 35, 64, 71), 190, 350, fill=color, width=width)
    return image

for icon in ("home", "approval", "profile"):
    for state, color in PALETTE.items():
        draw_icon(icon, color).save(OUT / f"{icon}-{state}.png")
