#!/usr/bin/env python3
"""Pull Ireland's finished games from API-Football through the site's Worker into tools/data/feed_matches.json.
Incremental: a game already stored is not fetched again. Feed coverage starts properly around 2017-18; see HANDOVER.md.
Run from the repo root, before build_archive.py."""
import json, os, sys, time, urllib.request
BASE = os.environ.get("SITE_BASE", "https://irelandfootball.richardmcallister.workers.dev")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
OUT = "tools/data/feed_matches.json"; TEAM = 776
YEARS = [2012, 2016] + list(range(2017, time.gmtime().tm_year + 1))
def get(path):
    for attempt in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=60).read().decode("utf-8"))
        except Exception as e:
            if attempt == 3: raise
            time.sleep(3 + attempt * 3)
store = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
fixtures = {}
for y in YEARS:
    print("year", y, flush=True)
    v = "&v=2" if y >= time.gmtime().tm_year - 1 else "&v=1"
    # the route caches a month, so the current years go through the live fixtures list as well
    for f in get(f"/api/team-season?season={y}{v}").get("response", []): fixtures[f["fixture"]["id"]] = f
for f in get("/api/fixtures?v=4").get("response", []): fixtures[f["fixture"]["id"]] = f
new = 0
for fid, f in sorted(fixtures.items(), key=lambda x: x[1]["fixture"]["timestamp"]):
    if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN") or str(fid) in store: continue
    j = get(f"/api/match?fixture={fid}&v=4"); r = (j.get("response") or [None])[0]
    if not r: continue
    home = r["teams"]["home"]["id"] == TEAM; us = TEAM
    goals = []; subs = []
    for e in r.get("events") or []:
        if e["type"] == "Goal" and e["detail"] != "Missed Penalty" and e["team"]["id"] == us:
            goals.append({"n": (e["player"] or {}).get("name"), "m": e["time"]["elapsed"], "x": e["time"]["extra"], "d": e["detail"]})
        if e["type"] == "subst" and e["team"]["id"] == us:
            subs.extend(x for x in ((e["player"] or {}).get("name"), (e["assist"] or {}).get("name")) if x)
    lu = next((l for l in r.get("lineups") or [] if l["team"]["id"] == us), None)
    store[str(fid)] = {"id": fid, "d": r["fixture"]["date"][:10], "home": home, "opp": (r["teams"]["away"] if home else r["teams"]["home"])["name"],
        "gf": r["goals"]["home"] if home else r["goals"]["away"], "ga": r["goals"]["away"] if home else r["goals"]["home"], "st": r["fixture"]["status"]["short"],
        "league": r["league"]["name"], "venue": (r["fixture"]["venue"] or {}).get("name"), "city": (r["fixture"]["venue"] or {}).get("city"), "goals": goals, "subs": subs,
        "xi": [p["player"]["name"] for p in lu["startXI"]] if lu else [], "bench": [p["player"]["name"] for p in lu["substitutes"]] if lu else [], "coach": (lu.get("coach") or {}).get("name") if lu else None, "form": lu.get("formation") if lu else None}
    new += 1; time.sleep(0.4)
    if new % 10 == 0: json.dump(store, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True); print("saved", len(store), flush=True)
json.dump(store, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
print("feed games", len(store), "new", new)
