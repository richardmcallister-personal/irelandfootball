#!/usr/bin/env python3
"""Match reports from 1986: reads Wikipedia's results-by-decade football boxes (tools/data/wiki_results_<decade>.txt,
CC BY-SA) and writes site/history/reports.json, keyed by date: goals at both ends with minutes, shoot-outs, ground,
crowd and referee. Every box is checked against the archive score; disagreements go to tools/data/reconcile_reports.txt
and that game keeps only what agrees. Run after build_archive.py."""
import glob, json, re, datetime
FROM = "1986-01-01"
M = json.load(open("site/history/matches.json", encoding="utf-8"))
P = json.load(open("site/history/players.json", encoding="utf-8"))
BY_WIKI = {p["wiki"].replace("_", " ").lower(): p for p in P if p.get("wiki")}
BY_NAME = {p["name"].lower(): p for p in P}
ARCH = {m["d"]: m for m in M}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
log = []

def strip(s):
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\{\{(?:flagicon|flag|fb|fb-rt|nowrap)\|([^}|]*)[^}]*\}\}", r"\1", s, flags=re.I)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"'{2,}", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,")

def date(s):
    s = strip(re.sub(r"\{\{(?:start date|date)[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}", r"\1-\2-\3", s, flags=re.I))
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m: return "%04d-%02d-%02d" % tuple(map(int, m.groups()))
    m = re.match(r"(\d{1,2}) ([A-Za-z]+),? (\d{4})", s) or re.match(r"([A-Za-z]+) (\d{1,2}),? (\d{4})", s)
    if not m: return None
    a, b, y = m.groups()
    d, mo = (a, b) if a.isdigit() else (b, a)
    return "%s-%02d-%02d" % (y, MONTHS[mo.lower()], int(d)) if mo.lower() in MONTHS else None

def person(chunk):
    """Name shown, full name (link target without the disambiguation) and link target."""
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", chunk)
    if m:
        tgt = m.group(1).strip(); full = re.sub(r"\s*\(.*?\)$", "", tgt)
        return full, tgt
    n = strip(re.sub(r"\{\{.*?\}\}", "", chunk))
    return n, None

def goals(field):
    out = []
    for part in re.split(r"<br\s*/?>|\n", field or ""):
        if not part.strip(): continue
        name, tgt = person(part)
        for t in re.findall(r"\{\{\s*(goal|og|pengoal|penmiss)\s*((?:\|[^}]*)?)\}\}", part, flags=re.I):
            kind, args = t[0].lower(), [a.strip() for a in t[1].split("|")[1:]]
            if kind == "og":
                out += [(name, tgt, a.rstrip("'′"), "og") for a in args if a]; continue
            cur = None
            for a in args:
                if re.match(r"^\d+(\+\d+)?['′]?$", a):
                    if cur: out.append(cur)
                    cur = [name, tgt, a.rstrip("'′"), ""]
                elif a and cur:
                    cur[3] = "p" if a.lower().startswith("pen") else "og" if a.lower().startswith("o") else ""
            if cur: out.append(cur)
    return [tuple(g) for g in out]

def shootout(field):
    out = []
    for part in re.split(r"<br\s*/?>|\n", field or ""):
        k = re.search(r"\{\{\s*(pengoal|penmiss)", part, flags=re.I)
        if k: out.append([person(part)[0], 1 if k.group(1).lower() == "pengoal" else 0])
    return out

def ireland_player(name, tgt, m):
    p = (BY_WIKI.get(tgt.lower()) if tgt else None) or BY_NAME.get(name.lower())
    if not p:  # surname only in the box: use the archive's scorer list for that game
        hits = [s[0] for s in (m.get("sc") or []) if s[0].split()[-1].lower() == name.split()[-1].lower()]
        if len(set(hits)) == 1: p = BY_NAME.get(hits[0].lower()) or {"name": hits[0]}
    return p

def mins(g):
    a = re.match(r"(\d+)(?:\+(\d+))?", g[2] or "0"); return int(a.group(1)) + int(a.group(2) or 0) / 100

R = {}
BOXED = set()
for f in sorted(glob.glob("tools/data/wiki_results_*.txt")):
    for x in re.findall(r"\|\s*date\s*=([^\n]*)", open(f, encoding="utf-8").read()):
        if date(x): BOXED.add(date(x))
OK_EXT = ("uefa.com", "fifa.com", "bbc.co", "rte.ie", "theguardian.com", "irishtimes.com", "independent.ie", "the42.ie", "web.archive.org")
for f in sorted(glob.glob("tools/data/wiki_results_*.txt")):
    txt = open(f, encoding="utf-8").read()
    for box in re.split(r"\{\{\s*football box", txt, flags=re.I)[1:]:
        F, key = {}, None
        for line in box.split("\n"):
            m = re.match(r"^\s*\|\s*([a-z0-9_]+)\s*=(.*)$", line)
            if m: key = m.group(1).lower(); F[key] = m.group(2).strip()
            elif key and line.strip() and not line.strip().startswith("}}"): F[key] += "\n" + line.strip()
            if line.strip().startswith("}}"): break
        d = date(F.get("date", ""))
        if not d or d < FROM: continue
        m = ARCH.get(d)
        if not m:  # a day apart between sources (kick-off across midnight, or a dating slip): take it when the neighbour has no box of its own
            for k in (-1, 1):
                n = (datetime.date.fromisoformat(d) + datetime.timedelta(days=k)).isoformat()
                if n in ARCH and n not in R and n not in BOXED:
                    log.append(f"{d}: Wikipedia's date; the archive has {n} v {ARCH[n]['o']}, used that game"); d, m = n, ARCH[n]; break
        if not m:
            log.append(f"{d}: on Wikipedia, not in the archive ({strip(F.get('team1',''))} v {strip(F.get('team2',''))})"); continue
        us1 = "IRL" in F.get("team1", "") or "Ireland" in F.get("team1", "")
        sc = re.match(r"\s*(\d+)\s*[–-]\s*(\d+)", strip(F.get("score", "")))
        if not sc:
            log.append(f"{d}: no score in the box"); continue
        a, b = int(sc.group(1)), int(sc.group(2)); gf, ga = (a, b) if us1 else (b, a)
        r = {}
        if (gf, ga) != (m["gf"], m["ga"]):
            log.append(f"{d} v {m['o']}: Wikipedia {gf}–{ga}, archive {m['gf']}–{m['ga']}; kept the ground, crowd and referee only")
        else:
            g1, g2 = goals(F.get("goals1")), goals(F.get("goals2"))
            gu, gt = (g1, g2) if us1 else (g2, g1)
            if (len(gu), len(gt)) != (gf, ga):
                log.append(f"{d} v {m['o']}: Wikipedia lists {len(gu)}+{len(gt)} goals for {gf}–{ga}; goals left out")
            else:
                G = []
                for side, lst in ((1, gu), (0, gt)):
                    for name, tgt, mn, ty in lst:
                        row = [side, name, mn, ty]
                        if side and ty != "og":
                            p = ireland_player(name, tgt, m)
                            if p: row[1] = p["name"]; row.append(p.get("slug", ""))
                            else: log.append(f"{d} v {m['o']}: Ireland scorer {name} not matched to a player")
                        G.append(row)
                r["g"] = sorted(G, key=mins)
        if F.get("aet", "").strip().lower() in ("yes", "y", "1"): r["aet"] = 1
        p1, p2 = shootout(F.get("penalties1")), shootout(F.get("penalties2"))
        if p1 or p2: r["pens"] = {"us": p1 if us1 else p2, "them": p2 if us1 else p1, "first": "us" if us1 else "them"}
        ground, loc = strip(F.get("stadium", "")), strip(F.get("location", ""))
        if ground: r["ground"] = ground
        if loc: r["loc"] = loc
        att = re.sub(r"[^\d]", "", strip(F.get("attendance", "")))
        if att: r["att"] = int(att)
        ref = F.get("referee", "")
        if strip(ref):
            nm, _ = person(ref) if "[[" in ref else (strip(ref), None)
            ctry = re.search(r"\(([^)]*)\)\s*$", strip(re.sub(r"\[\[[^\]]*\]\]", lambda x: strip(x.group(0)), ref)))
            r["ref"] = nm + (" (" + ctry.group(1) + ")" if ctry and ctry.group(1) not in nm else "")
        ext = re.search(r"https?://[^\s\]|}]+", F.get("report", ""))
        if ext and any(h in ext.group(0) for h in OK_EXT): r["ext"] = ext.group(0)
        R[d] = r

missing = [m["d"] + " v " + m["o"] for m in M if m["d"] >= FROM and m["d"] not in R]
for x in missing: log.append(f"{x}: no football box on Wikipedia; report built from the archive only")
json.dump(R, open("site/history/reports.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
open("tools/data/reconcile_reports.txt", "w", encoding="utf-8").write("Match reports: where Wikipedia's results boxes and the archive disagree (build_reports.py)\n\n" + "\n".join(log) + "\n")
n = sum(1 for m in M if m["d"] >= FROM)
print(f"{n} games from 1986, {len(R)} with a Wikipedia box, {sum(1 for r in R.values() if 'g' in r)} with goals, {len(log)} notes")
