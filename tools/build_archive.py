#!/usr/bin/env python3
"""Build site/history/*.json from tools/data/. No network. Run from the repo root.
Results and scorers: martj42/international_results (CC0). Venue, manager, match notes, caps: Wikipedia (CC BY-SA).
Writes tools/data/reconcile.txt listing every disagreement between the two, for review."""
import csv, json, os, re, unicodedata, collections as C, datetime as DT
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
# ---- feed: match-centre ids, games the dataset has not reached yet, scorers where the dataset has none, line-ups
FEED = json.load(open(D + "feed_matches.json", encoding="utf-8")) if os.path.exists(D + "feed_matches.json") else {}
FCOMP = [("World Cup - Qualification", "WCQ", "FIFA World Cup qualification"), ("World Cup", "WC", "FIFA World Cup"), ("Euro Championship - Qualification", "ECQ", "UEFA Euro qualification"), ("Euro Championship", "EC", "UEFA Euro"), ("Nations League", "NL", "UEFA Nations League"), ("Friendlies", "FR", "Friendly")]
FNAME = {"Rep. Of Ireland": T, "FYR Macedonia": "North Macedonia", "Czechia": "Czech Republic", "USA": "United States"}
byday = {r["d"]: r for r in rows}
def feedrow(f):
    day = DT.date.fromisoformat(f["d"])
    for x in (0, -1, 1):
        r = byday.get((day + DT.timedelta(days=x)).isoformat())
        if r: return r
    return None
for f in sorted(FEED.values(), key=lambda x: x["d"]):
    r = feedrow(f)
    if not r:
        c, t = next(((c, t) for k, c, t in FCOMP if k in f["league"]), ("FR", f["league"]))
        r = {"d": f["d"], "c": c, "t": t, "o": FNAME.get(f["opp"], f["opp"]), "h": 1 if f["home"] else -1, "gf": f["gf"], "ga": f["ga"], "city": f.get("city") or "", "ctry": "", "scf": 0}
        if f.get("venue"): r["v"] = f["venue"]
        rows.append(r); byday[f["d"]] = r; rec.append(f"FEED ONLY {f['d']} {r['o']} {f['gf']}-{f['ga']}")
    elif (r["gf"], r["ga"]) != (f["gf"], f["ga"]) and f["st"] == "FT": rec.append(f"FEED SCORE {r['d']} {r['o']}: archive {r['gf']}-{r['ga']}, feed {f['gf']}-{f['ga']}")
    r["id"] = f["id"]; r["_f"] = f
    if len(r.get("sc", [])) < r["gf"]:
        if len(f["goals"]) == r["gf"] and all(g["n"] for g in f["goals"]):
            r["sc"] = [[g["n"], (str(g["m"]) + ("+" + str(g["x"]) if g["x"] else ""))] + (["p"] if g["d"] == "Penalty" else ["og"] if g["d"] == "Own Goal" else []) for g in sorted(f["goals"], key=lambda g: (g["m"], g["x"] or 0))]
            r["scf"] = 1; r["_fs"] = 1
        else: rec.append(f"FEED SCORERS {r['d']} {r['o']}: {len(f['goals'])} goal events for {r['gf']} goals, not used")
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
def iso(s):  # Wikipedia writes most dates in full ("2 June 2013") and a few short ("2 Jun 2013", "2 Sept 2013")
    s = clean(s).replace("Sept ", "Sep ")
    for f in ("%d %B %Y", "%d %b %Y"):
        try: return DT.datetime.strptime(s, f).strftime("%Y-%m-%d")
        except Exception: pass
    return None
for m in re.finditer(r"\{\{sortname\|([^|}]*)\|([^|}]*)((?:\|[^}]*)?)\}\}(.*?)(?=<ref|\n\|-)", pt, re.S):
    a, b, extra, body = m.groups(); name = (a + " " + b).strip()
    f = re.search(r"([A-Z]{2}(?:/[A-Z]{2})?)\s*\|\|\s*(\d+)\s*\|\|\s*(\d+)\s*\|\|\s*([^|]*?)\s*\|\|.*?\{\{fb\|([^}|]*).*?\}\}\s*\|+\s*([^|]*?)\s*\|+.*?\{\{fb\|([^}|]*)", body, re.S)
    if not f: rec.append("PLAYER ROW NOT PARSED " + name); continue
    pos, caps, gl, deb, debo, last, lasto = f.groups()
    ex = extra.strip("|"); link = name + " (" + ex[4:] + ")" if ex.startswith("dab=") else (ex or name)
    players.append({"name": name, "slug": slug(name), "wiki": link.replace(" ", "_"), "pos": pos, "caps": int(caps), "goals": int(gl), "debut": iso(deb), "debo": debo, "last": iso(last), "lasto": lasto})
# Capped players missing from Wikipedia's list (found through the feed's line-ups). Their caps are counted from those line-ups.
for x in json.load(open(D + "extra_players.json", encoding="utf-8")):
    if not any(fold(p["name"]) == fold(x["name"]) for p in players):
        players.append({"name": x["name"], "slug": slug(x["name"]), "wiki": x["name"].replace(" ", "_"), "pos": x["pos"], "caps": 0, "goals": 0, "debut": None, "debo": "", "last": None, "lasto": "", "fromfeed": 1})
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
def feedwho(n, d):
    """A feed name, usually 'T. Parrott', to the caps list. The surname must match and the initial if there is one."""
    n = (n or "").replace("&apos;", "'").replace("’", "'"); n = {"Wesley Hoolahan": "Wes Hoolahan", "Michael Johnston": "Mikey Johnston"}.get(n, n); m = re.match(r"^([A-Z])\. ?(.*)$", n); ini, sn = (m.group(1).lower(), m.group(2)) if m else (None, n)
    sf = fold(sn); out = []
    for p in players:
        pf = fold(p["name"])
        if not (pf == sf or pf.endswith(" " + sf) or (not ini and sf.split()[-1:] == pf.split()[-1:] and sf.split()[:1] == pf.split()[:1])): continue
        if ini and not pf.startswith(ini): continue
        if p["debut"] and p["debut"] > d: continue
        out.append(p)
    return sorted(out, key=lambda p: p["last"] or "", reverse=True)[0] if out else None
# ---- named goals from Wikipedia's lists (tools/data/extra_goals.csv). Never overwrites: fills only goals the row has no name for, with no minute.
if os.path.exists(D + "extra_goals.csv"):
    for g in csv.DictReader(open(D + "extra_goals.csv", encoding="utf-8")):
        r = next((x for x in rows if x["d"] == g["date"] and x["o"] == g["opponent"]), None)
        if not r: rec.append(f"EXTRA GOALS NO ROW {g['date']} {g['opponent']} {g['scorer']}"); continue
        sc = r.setdefault("sc", []); need = int(g["goals"]) - sum(1 for s in sc if s[0] == g["scorer"]); room = r["gf"] - len(sc)
        if need < 0 or need > room: rec.append(f"EXTRA GOALS DO NOT FIT {g['date']} {g['opponent']} {g['scorer']}: {g['goals']} listed, {len(sc)} of {r['gf']} already named")
        sc.extend([g["scorer"], None] for _ in range(max(0, min(need, room))))
        if not sc: del r["sc"]
        if len(sc) >= r["gf"]: r["scf"] = 1
rec.append("DATE 1924 United States: match lists and US records say 14 June, Wikipedia's hat-tricks list says 16 June. Kept 14 June.")
rec.append("DATE 1929 Belgium: dataset 30 April, Wikipedia's hat-tricks list 20 April. Same game; kept the dataset date.")
rec.append("WIKI 2007 and 2012 Keane list: two goals dated 11 Nov 2007 and 9 Sep 2012, no game on those days. They match the archive's 17 Nov 2007 and 7 Sep 2012 goals.")
for d, t in (json.load(open(D + "note_fixes.json", encoding="utf-8")) if os.path.exists(D + "note_fixes.json") else {}).items():
    next(x for x in rows if x["d"] == d)["n"] = t
STORIES = json.load(open(D + "stories.json", encoding="utf-8")) if os.path.exists(D + "stories.json") else {"matches": [], "campaigns": []}
for s in STORIES["matches"]:
    x = next(x for x in rows if x["d"] == s["d"]); x["bm"] = s["slug"]; x["bml"] = s["label"]
for s in STORIES["campaigns"]:
    for x in rows:
        if s["from"] <= x["d"] <= s["to"] and x["c"] in s["comps"]: x["camp"] = s["slug"]; x["campn"] = s["name"]
apps = C.defaultdict(list); lineups = {}; nomatch = C.Counter()
for r in rows:
    f = r.pop("_f", None)
    if r.pop("_fs", None):
        for s in r["sc"]:
            p = feedwho(s[0], r["d"]) if "og" not in s else None
            if p: s[0] = p["name"]
            elif "og" not in s: nomatch[s[0]] += 1
    if not f or not f["xi"]: continue
    onfield = set(f["subs"]); L = {"form": f.get("form"), "coach": f.get("coach"), "xi": [], "bench": []}
    for key, names in (("xi", f["xi"]), ("bench", f["bench"])):
        for n in names:
            p = feedwho(n, r["d"]); e = {"n": p["name"] if p else n.replace("&apos;", "'")}
            if p: e["s"] = p["slug"]
            elif key == "xi": nomatch[n] += 1
            if key == "bench" and n in onfield: e["on"] = 1
            L[key].append(e)
            if p and (key == "xi" or n in onfield): apps[p["slug"]].append({"i": r["d"], "o": r["o"], "st": 1 if key == "xi" else 0, "id": r.get("id")})
    lineups[r["d"]] = L
for n, c in nomatch.most_common(): rec.append(f"FEED NAME NOT IN CAPS LIST {n} ({c})")
json.dump(lineups, open(OUT + "lineups.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(apps, open(OUT + "player_apps.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
sbl = C.defaultdict(list); unknown = C.Counter()
for r in rows:
    for s in r.get("sc", []):
        if "og" in s: continue
        p = who(s[0], r["d"])
        if p: sbl[p["slug"]].append({"d": r["d"], "o": r["o"], "i": r["i"], "m": s[1], "p": 1 if "p" in s else 0, "c": r["c"]})
        else: unknown[s[0]] += 1
for p in players:
    n = len(sbl.get(p["slug"], [])); p["known"] = n
    if n > p["goals"]:
        if not p.get("fromfeed"): rec.append(f"GOALS {p['name']}: dataset {n}, Wikipedia {p['goals']}")
        p["goals"] = n   # Wikipedia's list lags the latest games
    A = apps.get(p["slug"], [])
    if len(A) > p["caps"]:
        if not p.get("fromfeed"): rec.append(f"CAPS {p['name']}: line-ups {len(A)}, Wikipedia {p['caps']}")
        p["caps"] = len(A)
    if A and (not p["last"] or A[-1]["i"] > p["last"]): p["last"], p["lasto"] = A[-1]["i"], A[-1]["o"]
    if A and not p["debut"]: p["debut"], p["debo"] = A[0]["i"], A[0]["o"]
for n, c in unknown.most_common(): rec.append(f"SCORER NOT IN CAPS LIST {n} ({c})")
players.sort(key=lambda p: (-p["caps"], p["name"]))
json.dump(players, open(OUT + "players.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(sbl, open(OUT + "player_goals.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- managers (Wikipedia table: one row per spell; a person with two spells gets one page)
tt = open(D + "wiki_team.txt", encoding="utf-8").read(); i = tt.find("===Coaching history==="); j = tt.find("\n==Players==", i); mt = tt[i:j]; mgrs = []
WIKI_FIX = json.load(open(D + "manager_wiki.json", encoding="utf-8"))   # checked article titles; null = no article
for block in mt.split("\n|-")[2:]:
    cells = [c[1:].strip() if c.startswith("|") else c for c in block.strip().split("\n")]
    if len(cells) < 9: continue
    nm = cells[0]; sm = re.search(r"\{\{sortname\|([^|}]*)\|([^|}]*)", nm)
    name = (sm.group(1) + " " + sm.group(2)).strip() if sm else clean(re.sub(r"style=\"[^\"]*\"\|?", "", nm))
    nums = [clean(c) for c in cells[2:8]]
    try: p, w, d, l, gf, ga = [int(re.sub(r"[^\d]", "", n)) for n in nums]
    except ValueError: continue
    note = clean(re.sub(r'style="[^"]*"\s*\|?', "", cells[-1])) if len(cells) > 11 else ""
    yrs = re.findall(r"\d{4}", clean(cells[1]))
    mgrs.append({"name": name, "slug": slug(name.replace(", Sr.", "")), "career": clean(cells[1]), "from": int(yrs[0]), "to": int(yrs[-1]) if len(yrs) > 1 or not clean(cells[1]).endswith("–") else 9999, "p": p, "w": w, "d": d, "l": l, "gf": gf, "ga": ga, "note": note[:160]})
def same(ms, s): return all(tally(ms)[k] == s[k] for k in ("p", "w", "d", "l", "gf", "ga"))
def spell_for(surname, y):
    f = [s for s in mgrs if fold(s["name"].replace(", Sr.", "")).split()[-1] == fold(surname).split()[-1] and s["from"] <= y <= s["to"]]
    return f[0] if f else None
# 1. Where Wikipedia's match list names a manager, use it; a row with no name takes the previous row's manager if his spell covers that year.
for r in rows:
    s = spell_for(r["m"], int(r["d"][:4])) if r.get("m") and r["m"] not in ("OCI", "FAIFS", "FAI") else None
    if s: r["_s"] = s
prev = None
for r in rows:
    if "_s" in r: prev = r["_s"]
    elif not r.get("m") and prev and int(r["d"][:4]) <= prev["to"]: r["_s"] = prev
# 2. Before 1969 the list only says "FAI". Assign a spell's games only where one unbroken run inside its years matches Wikipedia's figures exactly, and only one run does.
for s in mgrs:
    if any(r.get("_s") is s for r in rows) or not s["p"]: continue
    free = [r for r in rows if "_s" not in r and s["from"] <= int(r["d"][:4]) <= s["to"]]
    hits = [free[a:a + s["p"]] for a in range(len(free) - s["p"] + 1) if same(free[a:a + s["p"]], s)]
    if len(hits) == 1:
        for r in hits[0]: r["_s"] = s
    else: rec.append(f"MANAGER GAMES NOT PLACED {s['name']} {s['career']}: {len(hits)} possible runs")
for s in mgrs:
    ms = [r for r in rows if r.get("_s") is s]; s["listed"] = len(ms)
    if ms and not same(ms, s): rec.append(f"MANAGER FIGURES {s['name']} {s['career']}: games {tally(ms)}, Wikipedia P{s['p']} W{s['w']} D{s['d']} L{s['l']} GF{s['gf']} GA{s['ga']}")
for r in rows:
    s = r.pop("_s", None)
    if s: r["ms"] = s["slug"]; r["mn"] = s["name"]
    r.pop("m", None)
for s in mgrs:
    s["wiki"] = WIKI_FIX.get(s["slug"], s["name"].replace(" ", "_")) if s["slug"] != "selection-committee" else None
json.dump(rows, open(OUT + "matches.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
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
for m in {x["slug"]: x for x in mgrs}.values(): S.append([m["name"], "manager", "/manager/?m=" + m["slug"], f"{m['career']} · {m['p']} games", []])
for k, v in sorted(dec.items()): S.append([k, "season", "/results/?dec=" + k[:4], f"{len(v)} games", []])
for s in STORIES["matches"]: S.append([s["title"], "match", "/matches/" + s["slug"] + "/", s["desc"], []])
for s in STORIES["campaigns"]: S.append([s["title"], "match", "/campaigns/" + s["slug"] + "/", s["desc"], []])
json.dump(S, open("site/search.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump({"archive": {"date": DT.date.today().isoformat(), "note": f"{len(rows)} matches to {rows[-1]['d']}"}}, open("site/status.json", "w"), indent=0)
open(D + "reconcile.txt", "w", encoding="utf-8").write("\n".join(rec) + "\n")
A = R["all"]; print("matches", len(rows), A, "players", len(players), "managers", len(mgrs), "opps", len(opps), "reconcile", len(rec), "scored", scored, "of", tg, "unknown scorers", len(unknown))
