"""Draw the News Mood app icon (assets/icon.png, 1024x1024)."""

from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.png"

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Background tile with a soft vertical gradient (macOS icon grid: ~10% margin).
m, r = 100, 185
grad = Image.new("RGBA", (S, S))
gd = ImageDraw.Draw(grad)
for y in range(S):
    t = y / S
    gd.line([(0, y), (S, y)], fill=(int(28 + 20 * t), int(36 + 14 * t), int(64 + 30 * t), 255))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m], r, fill=255)
img.paste(grad, (0, 0), mask)

# "Newspaper" lines.
for i, w in enumerate([520, 520, 430, 520, 360]):
    y = 300 + i * 70
    d.rounded_rectangle([250, y, 250 + w, y + 28], 14, fill=(225, 230, 242, 235))

# Mood arrows: up (green) and down (red).
d.polygon([(330, 760), (430, 640), (530, 760)], fill=(52, 199, 89, 255))
d.polygon([(500, 640), (600, 760), (700, 640)], fill=(255, 69, 58, 255))

OUT.parent.mkdir(exist_ok=True)
img.save(OUT)
print(OUT)
