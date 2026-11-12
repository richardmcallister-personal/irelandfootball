#!/usr/bin/env python3
"""Web copies of the front-page photos: tools/data/photos/photos.csv says which source file fills which slot, how to crop it
and whom to credit. Writes site/assets/photos/<slot>-<width>.jpg and site/assets/photos/credits.json (shown under the doors).
Only free-licence photos or ones Richard has the right to publish belong here; never a watermarked agency preview."""
import csv, json, os
from PIL import Image, ImageOps
SRC, OUT = "tools/data/photos/", "site/assets/photos/"
os.makedirs(OUT, exist_ok=True); credits = {}
for r in csv.DictReader(open(SRC + "photos.csv", encoding="utf-8")):
    im = ImageOps.exif_transpose(Image.open(SRC + r["file"])).convert("RGB")
    a, b = map(int, r["crop"].split(":")); W, H = im.size; t = a / b
    cw, ch = (H * t, H) if W / H > t else (W, W / t)
    x = min(max(float(r["focus_x"]) * W - cw / 2, 0), W - cw); y = min(max(float(r["focus_y"]) * H - ch / 2, 0), H - ch)
    im = im.crop((round(x), round(y), round(x + cw), round(y + ch)))
    for w in (480, 960, 1600):
        if w > im.width and w != 480: continue
        im.resize((w, round(w / t)), Image.LANCZOS).save(f"{OUT}{r['slot']}-{w}.jpg", quality=80, optimize=True, progressive=True)
    credits[r["slot"]] = {k: r[k] for k in ("credit", "licence", "url", "status")}
json.dump(credits, open(OUT + "credits.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(sorted(os.listdir(OUT)))
