#!/usr/bin/env python3
"""Turn the shirt catalogue (tools/data/kits_catalogue.csv, from the James Nolan Memorial Collection, irelandsoccershirts.com)
into site/kits/library.json for the Kits page. Web-size copies live in site/assets/kits/lib/<id>.jpg, watermarks untouched.
Views of one shirt are paired by era, category and caption: the first view is the front unless listed in BACK_FIRST.
Run from the repo root: python3 tools/build_kits.py"""
import csv, json, os, re
KEEP = {"home": "Home", "away": "Away", "third": "Third", "goalkeeper": "Goalkeeper", "reproduction": "Other", "historical-interleague": "Other"}
BACK_FIRST = set(json.load(open("tools/data/kits_back_first.json"))) if os.path.exists("tools/data/kits_back_first.json") else set()
# Same shirt, front then back, where the source captions differ slightly. 0512 and 0513 stay apart: their captions name different opponents.
PAIRS = {"0020": "0021", "0092": "0093", "0051": "0053", "0471": "0472"}
R = [r for r in csv.DictReader(open("tools/data/kits_catalogue.csv", encoding="utf-8")) if r["category"] in KEEP]
def norm(c): return re.sub(r"[^a-z0-9]+", " ", c.lower()).strip()
eras = {}; order = []
for r in sorted(R, key=lambda r: r["id"]):
    os.path.exists(f"site/assets/kits/lib/{r['id']}.jpg") or print("missing", r["id"])
    key = r["source_era"]
    if key not in eras:
        eras[key] = {"era": key.replace(" - ", "–").replace("-", "–").replace("Pre 1966", "Before 1966"), "y": min(int(x["year_start"]) for x in R if x["source_era"] == key), "page": r["source_page"], "shirts": []}; order.append(key)
    L = eras[key]["shirts"]; last = L[-1] if L else None
    if last and PAIRS.get(last["v"][0]) == r["id"]:
        last["v"].append(r["id"])
    elif last and last["k"] == KEEP[r["category"]] and last["_c"] == r["category"] and norm(last["cap"]) == norm(r["caption"]) and len(last["v"]) < 2 and int(r["id"]) - int(last["v"][-1]) <= 2:
        last["v"].append(r["id"])
    else:
        L.append({"k": KEEP[r["category"]], "_c": r["category"], "cap": r["caption"].rstrip("."), "yl": r["year_label"], "v": [r["id"]]})
for e in eras.values():
    for s in e["shirts"]:
        if s["v"][0] in BACK_FIRST: s["v"].reverse()
        s["other"] = {"reproduction": "Reproduction", "historical-interleague": "Inter-league"}.get(s.pop("_c"))
        if not s["other"]: del s["other"]
out = sorted(eras.values(), key=lambda e: -e["y"])
json.dump({"credit": "Photos: Eddie O’Mahony, James Nolan Memorial Collection", "home": "https://www.irelandsoccershirts.com/james-nolan-memorial-collection/", "eras": out}, open("site/kits/library.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "eras", sum(len(e["shirts"]) for e in out), "shirts", sum(len(s["v"]) for e in out for s in e["shirts"]), "photos", sum(1 for e in out for s in e["shirts"] if len(s["v"]) == 1), "single views")
