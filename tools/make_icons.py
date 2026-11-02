#!/usr/bin/env python3
"""Build every crest size and app icon from site/assets/crest.png. With no crest.png, draws a plain placeholder first.
Run from the repo root after replacing the crest. iPhone launch images are added once the real crest arrives."""
import os
from PIL import Image, ImageDraw, ImageFont
A = "site/assets/"; GREEN = (11, 110, 79, 255)
if not os.path.exists(A + "crest.png"):
    im = Image.new("RGBA", (540, 540), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.ellipse((10, 10, 530, 530), fill=(255, 255, 255, 255)); d.ellipse((34, 34, 506, 506), fill=GREEN)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 170); t = "IRL"; b = d.textbbox((0, 0), t, font=f)
    d.text((270 - (b[2] - b[0]) / 2 - b[0], 270 - (b[3] - b[1]) / 2 - b[1]), t, font=f, fill=(255, 255, 255, 255)); im.save(A + "crest.png")
c = Image.open(A + "crest.png").convert("RGBA")
def fit(s, pad=0, bg=None):
    o = Image.new("RGBA", (s, s), bg or (0, 0, 0, 0)); n = s - 2 * pad; r = c.copy(); r.thumbnail((n, n), Image.LANCZOS); o.alpha_composite(r, ((s - r.width) // 2, (s - r.height) // 2)); return o
for s in (44, 88, 132): fit(s).save(f"{A}crest-{s}.png")
fit(32).save(A + "favicon-32.png"); fit(96).save(A + "badge-96.png")
fit(180, 14, GREEN).convert("RGB").save(A + "apple-touch-icon.png"); fit(192, 14, GREEN).save(A + "icon-192.png"); fit(512, 36, GREEN).save(A + "icon-512.png"); fit(512, 90, GREEN).save(A + "icon-512-maskable.png")
print("icons done")
