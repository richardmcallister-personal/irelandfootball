#!/usr/bin/env python3
"""Build site/history/*.json from tools/data/. No network. Run from the repo root.
Results and scorers: martj42/international_results (CC0). Venue, manager, match notes, caps: Wikipedia (CC BY-SA).
Writes tools/data/reconcile.txt listing every disagreement between the two, for review."""
import csv, json, re, unicodedata, collections as C, datetime as DT
T = "Republic of Ireland"; OUT = "site/history/"; D = "tools/data/"
def rd(f): return list(csv.DictReader(open(D + f + ".csv", encoding="utf-8")))
def fold(s): return re.sub(r"[^a-z0-9 ]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip()
def slug(s): return re.sub(r" +", "-", fold(s.replace("-", " ")))
def clean(t):
    t = re.sub(r"<ref[^>]*/>", "", t); t = re.sub(r"<ref.*?(</ref>|$)", "", t, flags=re.S); t = re.sub(r"<[^>]+>", "", t)
    for _ in range(3): t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t); t = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", t)
    return re.sub(r"\s+", " ", t.replace("''", "").replace("&nbsp;", " ")).strip(" |")
COMP = {"Friendly": "FR", "FIFA World Cup qualification": "WCQ", "FIFA World Cup": "WC", "UEFA Euro qualification": "ECQ", "UEFA Euro": "EC", "UEFA Nations League": "NL", "Olympic Games": "OLY"}
COMPNAME = {"WC": "World Cup finals", "EC": "Euros finals", "WCQ": "World Cup qualifying", "ECQ": "Euros qualifying", "NL": "Nations League", "OLY": "Olympic Games", "FR": "Friendlies"}
rec = []
out = []
# ---- Wikipedia match list, keyed by date
wiki = C.defaultdict(list); wt = re.sub(r"<!--.*?-->", "", open(D + "wiki_matches.txt", encoding="utf-8").read(), flags=re.S)
for block in re.split(r"\n\|-", wt):
    m = re.search(r"^\s*\|(?:\s*style=\"[^\"]*\"\s*\|)?\s*(\d{4}-\d{2}-\d{2})\s*\|\|(.*)", block, re.M | re.S)
    if not m: continue
    cells = m.group(2).split("||")
    if len(cells) < 5: continue
    score = re.sub(r"^.*\|", "", cells[3]) if "|" in cells[3] else cells[3]
    sm = re.search(r"(\d+)\s*[–-]\s*(\d+)", clean(score))
    notes = clean("||".join(cells[5:]).split("\n")[0]) if len(cells) > 5 else ""
    wiki[m.group(1)].append({"comp": clean(cells[0]), "venue": clean(cells[1].split("\n")[0]), "opp": clean(cells[2]), "gf": int(sm.group(1)) if sm else None, "ga": int(sm.group(2)) if sm else None, "mgr": clean(cells[4]), "note": notes[:400]})
# ---- scorers
goals = C.defaultdict(list)
for g in rd("goalscorers"):
    goals[(g["date"], g["home_team"], g["away_team"])].append(g)
pens = {(s["date"], s["home_team"], s["away_team"]): s["winner"] for s in rd("shootouts")}
# ---- matches
rows = []; used = set()
EXTRA = list(csv.DictReader(open(D + "extra_matches.csv", encoding="utf-8")))   # official-looking games the dataset lacks; see the file
def wikirow(d, opp):
    """Wikipedia's row for this match: same date, or a day either side when the opponent's name agrees (time-zone differences)."""
    if d in wiki and len(wiki[d]) == 1: return d, wiki[d][0]
    day = DT.date.fromisoformat(d)
    for delta in (-1, 1):
        o = (day + DT.timedelta(days=delta)).isoformat()
        for c in wiki.get(o, []):
            if fold(opp) in fold(c["opp"]) or fold(c["opp"]) in fold(opp): return o, c
    return None, None
RENAME = {("Russia", 0, 1991): "Soviet Union", ("Germany", 1949, 1990): "West Germany"}
for r in rd("results") + EXTRA:
    home = r["home_team"] == T; opp = r["away_team"] if home else r["home_team"]
    gf, ga = (int(r["home_score"]), int(r["away_score"])) if home else (int(r["away_score"]), int(r["home_score"]))
    d = r["date"]; y = int(d[:4]); neutral = r["neutral"] == "TRUE"
    shown = opp
    if opp == "Russia" and d < "1992-01-01": shown = "Soviet Union"
    if opp == "Germany" and "1949-09-01" <= d < "1990-10-03": shown = "West Germany"
    wd, w = wikirow(d, shown)
    if w: used.add((wd, w["opp"]))
    k = (d, r["home_team"], r["away_team"]); gs = goals.get(k, [])
    sc = []; own = 0
    for g in sorted(gs, key=lambda x: float(x["minute"] or 0)):
        if g["team"] == T:
            s = [g["scorer"], g["minute"] or None]
            if g["penalty"] == "TRUE": s.append("p")
            if g["own_goal"] == "TRUE": s.append("og")
            sc.append(s)
    c = COMP.get(r["tournament"], "FR")
    row = {"d": d, "c": c, "t": r["tournament"], "o": shown, "h": 0 if neutral else (1 if home else -1), "gf": gf, "ga": ga, "city": r["city"], "ctry": r["country"]}
    if sc: row["sc"] = sc
    row["scf"] = 1 if len(sc) >= gf else 0    # 1 = every Ireland goal has a scorer
    if k in pens: row["pw"] = 1 if pens[k] == T else 0
    if w:
        v = w["venue"]; row["v"] = v
        if w["mgr"] not in ("", "–"): row["m"] = w["mgr"]
        if w["note"]: row["n"] = w["note"]
        if wd != d: rec.append(f"DATE {shown}: dataset {d}, Wikipedia {wd}")
        if k not in pens and w["gf"] is not None and (w["gf"], w["ga"]) != (gf, ga): rec.append(f"SCORE {d} {shown}: dataset {gf}-{ga}, Wikipedia {w['gf']}-{w['ga']}")
    else:
        rec.append(f"NO WIKI ROW {d} {shown} {gf}-{ga}")
    rows.append(row)
for d, cs in sorted(wiki.items()):
    for c in cs:
        if (d, c["opp"]) not in used: rec.append(f"WIKI ONLY {d} {c['opp']} {c['gf']}-{c['ga']} [{c['comp']}] {c['note'][:70]}")
rows.sort(key=lambda r: r["d"])
for i, r in enumerate(rows): r["i"] = i + 1
def res(r): return "W" if r["gf"] > r["ga"] else "L" if r["gf"] < r["ga"] else "D"
def tally(ms):
    t = {"p": len(ms), "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0}
    for m in ms: t[res(m).lower()] += 1; t["gf"] += m["gf"]; t["ga"] += m["ga"]
    return t
def brief(r): return {k: r[k] for k in ("d", "c", "o", "h", "gf", "ga", "i", "sc", "city", "v") if k in r}
json.dump(rows, open(OUT + "matches.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- opponents
byopp = C.defaultdict(list)
for r in rows: byopp[r["o"]].append(r)
opps = []
for o, ms in byopp.items():
    t = tally(ms); t.update({"name": o, "slug": slug(o), "first": ms[0]["d"], "last": ms[-1]["d"]}); opps.append(t)
opps.sort(key=lambda x: (-x["p"], x["name"]))
json.dump(opps, open(OUT + "opponents.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- players (Wikipedia caps list + dataset goals)
pt = open(D + "wiki_players.txt", encoding="utf-8").read(); players = []
def iso(s):
    try: return DT.datetime.strptime(clean(s), "%d %B %Y").strftime("%Y-%m-%d")
    except Exception: return None
for m in re.finditer(r"\{\{sortname\|([^|}]*)\|([^|}]*)((?:\|[^}]*)?)\}\}(.*?)(?=<ref|\n\|-)", pt, re.S):
    a, b, extra, body = m.groups(); name = (a + " " + b).strip()
    f = re.search(r"([A-Z]{2}(?:/[A-Z]{2})?)\s*\|\|\s*(\d+)\s*\|\|\s*(\d+)\s*\|\|\s*([^|]*?)\s*\|\|.*?\{\{fb\|([^}|]*).*?\}\}\s*\|+\s*([^|]*?)\s*\|+.*?\{\{fb\|([^}|]*)", body, re.S)
    if not f: rec.append("PLAYER ROW NOT PARSED " + name); continue
    pos, caps, gl, deb, debo, last, lasto = f.groups()
    ex = extra.strip("|"); link = name + " (" + ex[4:] + ")" if ex.startswith("dab=") else (ex or name)
    players.append({"name": name, "slug": slug(name), "wiki": link.replace(" ", "_"), "pos": pos, "caps": int(caps), "goals": int(gl), "debut": iso(deb), "debo": debo, "last": iso(last), "lasto": lasto})
seen = C.Counter(p["slug"] for p in players)
if max(seen.values(), default=0) > 1:
    idx = C.Counter()
    for p in players:
        if seen[p["slug"]] > 1:
            idx[p["slug"]] += 1
            if idx[p["slug"]] > 1: p["slug"] += "-" + str(idx[p["slug"]])
bynm = C.defaultdict(list)
for p in players: bynm[fold(p["name"])].append(p)
def who(name, d):
    c = bynm.get(fold(name), [])
    for p in c:
        if p["debut"] and p["last"] and p["debut"] <= d <= p["last"]: return p
    return c[0] if len(c) == 1 else None
sbl = C.defaultdict(list); unknown = C.Counter()
for r in rows:
    for s in r.get("sc", []):
        if "og" in s: continue
        p = who(s[0], r["d"])
        if p: sbl[p["slug"]].append({"d": r["d"], "o": r["o"], "i": r["i"], "m": s[1], "p": 1 if "p" in s else 0, "c": r["c"]})
        else: unknown[s[0]] += 1
for p in players:
    n = len(sbl.get(p["slug"], [])); p["known"] = n
    if n > p["goals"]: rec.append(f"GOALS {p['name']}: dataset {n}, Wikipedia {p['goals']}")
for n, c in unknown.most_common(): rec.append(f"SCORER NOT IN CAPS LIST {n} ({c})")
players.sort(key=lambda p: (-p["caps"], p["name"]))
json.dump(players, open(OUT + "players.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(sbl, open(OUT + "player_goals.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- managers (Wikipedia table)
tt = open(D + "wiki_team.txt", encoding="utf-8").read(); i = tt.find("===Coaching history==="); j = tt.find("\n==Players==", i); mt = tt[i:j]; mgrs = []
for block in mt.split("\n|-")[2:]:
    cells = [c[1:].strip() if c.startswith("|") else c for c in block.strip().split("\n")]
    if len(cells) < 9: continue
    nm = cells[0]; sm = re.search(r"\{\{sortname\|([^|}]*)\|([^|}]*)", nm)
    name = (sm.group(1) + " " + sm.group(2)).strip() if sm else clean(re.sub(r"style=\"[^\"]*\"\|?", "", nm))
    nums = [clean(c) for c in cells[2:8]]
    try: p, w, d, l, gf, ga = [int(re.sub(r"[^\d]", "", n)) for n in nums]
    except ValueError: continue
    note = clean(re.sub(r'style="[^"]*"\s*\|?', "", cells[-1])) if len(cells) > 11 else ""
    mgrs.append({"name": name, "career": clean(cells[1]), "p": p, "w": w, "d": d, "l": l, "gf": gf, "ga": ga, "note": note[:160]})
json.dump(mgrs, open(OUT + "managers.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- records
def runs(pred):
    best = []; cur = []
    for r in rows:
        if pred(r): cur.append(r)
        else:
            if cur: best.append(cur)
            cur = []
    if cur: best.append(cur)
    best.sort(key=lambda x: -len(x)); x = best[0] if best else []
    return {"n": len(x), "from": x[0]["d"], "to": x[-1]["d"], "cur": len(best and cur)} if x else None
home = [r for r in rows if r["h"] == 1]; away = [r for r in rows if r["h"] == -1]; neut = [r for r in rows if r["h"] == 0]
dec = C.defaultdict(list)
for r in rows: dec[r["d"][:3] + "0s"].append(r)
comps = C.defaultdict(list)
for r in rows: comps[r["c"]].append(r)
hat = []
for r in rows:
    c = C.Counter(s[0] for s in r.get("sc", []) if "og" not in s)
    for n, k in c.items():
        if k >= 3: hat.append({"name": n, "g": k, **brief(r)})
years = {}
vc = C.Counter()
for r in rows:
    if r["h"] == 1 and r.get("v"):
        parts = [x.strip() for x in r["v"].split(",") if x.strip() and fold(x) != fold(r["city"]) and fold(x) != fold(r["ctry"])]
        if parts: vc[parts[-1]] += 1
scored = sum(len([s for s in r.get("sc", []) if "og" not in s]) for r in rows); tg = sum(r["gf"] for r in rows)
sheets = lambda r: r["ga"] == 0
R = {"span": [rows[0]["d"], rows[-1]["d"]], "all": tally(rows), "home": tally(home), "away": tally(away), "neutral": tally(neut),
     "comps": [{"c": c, "name": COMPNAME[c], **tally(comps[c])} for c in COMPNAME if c in comps],
     "decades": [{"dec": k, **tally(v)} for k, v in sorted(dec.items())],
     "wins": [brief(r) for r in sorted(rows, key=lambda r: (-(r["gf"] - r["ga"]), -r["gf"], r["d"]))[:10]],
     "defeats": [brief(r) for r in sorted(rows, key=lambda r: (r["gf"] - r["ga"], -r["ga"], r["d"]))[:10]],
     "highest": [brief(r) for r in sorted(rows, key=lambda r: (-(r["gf"] + r["ga"]), r["d"]))[:5]],
     "runs": {"Won in a row": runs(lambda r: res(r) == "W"), "Unbeaten": runs(lambda r: res(r) != "L"), "Without a win": runs(lambda r: res(r) != "W"), "Lost in a row": runs(lambda r: res(r) == "L"), "Scored in": runs(lambda r: r["gf"] > 0), "Without scoring": runs(lambda r: r["gf"] == 0), "Clean sheets": runs(sheets)},
     "caps": [{k: p[k] for k in ("name", "slug", "caps", "goals", "debut", "last", "pos")} for p in players[:15]],
     "scorers": [{k: p[k] for k in ("name", "slug", "caps", "goals", "debut", "last")} for p in sorted(players, key=lambda p: (-p["goals"], p["caps"]))[:15]],
     "hats": sorted(hat, key=lambda h: h["d"]), "grounds": vc.most_common(12), "coverage": {"scored": scored, "goals": tg, "byComp": [{"c": c, "name": COMPNAME[c], "known": sum(len([s for s in r.get("sc", []) if "og" not in s]) + len([s for s in r.get("sc", []) if "og" in s]) for r in comps[c]), "goals": sum(r["gf"] for r in comps[c])} for c in COMPNAME if c in comps]}}
json.dump(R, open(OUT + "records.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- search index: [label, kind, url, sub, aliases]
S = []
for p in players: S.append([p["name"], "player", "/player/?p=" + p["slug"], f"{p['pos']} · {(p['debut'] or '')[:4]}–{(p['last'] or '')[:4]} · {p['caps']} caps, {p['goals']} goals", []])
for o in opps: S.append([o["name"], "club", "/opponent/?o=" + o["slug"], f"{o['p']} games, {o['w']} wins", []])
for m in mgrs: S.append([m["name"], "manager", "/managers/", f"{m['career']} · {m['p']} games", []])
for k, v in sorted(dec.items()): S.append([k, "season", "/results/?dec=" + k[:4], f"{len(v)} games", []])
json.dump(S, open("site/search.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump({"archive": {"date": DT.date.today().isoformat(), "note": f"{len(rows)} matches to {rows[-1]['d']}"}}, open("site/status.json", "w"), indent=0)
open(D + "reconcile.txt", "w", encoding="utf-8").write("\n".join(rec) + "\n")
A = R["all"]; print("matches", len(rows), A, "players", len(players), "managers", len(mgrs), "opps", len(opps), "reconcile", len(rec), "scored", scored, "of", tg, "unknown scorers", len(unknown))
