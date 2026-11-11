"""Read Wikipedia's tournament articles (tools/data/campaigns/*.txt, CC BY-SA): every football box (date, teams, score, goals,
extra time, shoot-out, ground) and the group table (Module:Sports table), for the campaign pages."""
import datetime, re
D = "tools/data/campaigns/"
CODES = {"ALB": "Albania", "AND": "Andorra", "ARM": "Armenia", "BEL": "Belgium", "BIH": "Bosnia and Herzegovina", "CMR": "Cameroon", "CRO": "Croatia",
         "CYP": "Cyprus", "DEN": "Denmark", "EGY": "Egypt", "ENG": "England", "ESP": "Spain", "EST": "Estonia", "FRA": "France", "GEO": "Georgia",
         "GER": "Germany", "FRG": "West Germany", "GIB": "Gibraltar", "HUN": "Hungary", "IRL": "Ireland", "IRN": "Iran", "ITA": "Italy", "KSA": "Saudi Arabia",
         "LTU": "Lithuania", "LVA": "Latvia", "LAT": "Latvia", "MEX": "Mexico", "MKD": "North Macedonia", "MLT": "Malta", "NED": "Netherlands", "NIR": "Northern Ireland",
         "NOR": "Norway", "POL": "Poland", "POR": "Portugal", "ROU": "Romania", "RUS": "Russia", "SCO": "Scotland", "SVK": "Slovakia", "SWE": "Sweden",
         "TCH": "Czechoslovakia", "URS": "Soviet Union", "HUN": "Hungary", "UKR": "Ukraine", "TUR": "Turkey", "SUI": "Switzerland", "BUL": "Bulgaria",
         "USA": "United States", "COL": "Colombia", "ARG": "Argentina", "BRA": "Brazil", "CRC": "Costa Rica", "KOR": "South Korea", "JPN": "Japan", "SEN": "Senegal", "BOL": "Bolivia", "MNE": "Montenegro", "CZE": "Czech Republic", "SVN": "Slovenia", "NIR": "Northern Ireland", "HUN": "Hungary", "CHN": "China", "TUN": "Tunisia", "URU": "Uruguay", "PAR": "Paraguay", "RSA": "South Africa", "SLO": "Slovenia", "CRO": "Croatia", "GRE": "Greece", "AUT": "Austria", "HUN": "Hungary", "ISL": "Iceland", "WAL": "Wales", "KOR": "South Korea", "CMR": "Cameroon", "NGA": "Nigeria", "MAR": "Morocco", "SAU": "Saudi Arabia", "BUL": "Bulgaria", "ROM": "Romania", "CSK": "Czechoslovakia", "YUG": "Yugoslavia"}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}

def strip(s):
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"'{2,}", "", s)
    return re.sub(r"\s+", " ", s).strip(" ,")

def date(s):
    m = re.search(r"\{\{\s*(?:start date|date)[^|]*\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})", s, flags=re.I)
    if m: return "%04d-%02d-%02d" % tuple(map(int, m.groups()))
    s = strip(s)
    m = re.search(r"(\d{1,2}) ([A-Za-z]+),? (\d{4})", s) or re.search(r"([A-Za-z]+) (\d{1,2}),? (\d{4})", s)
    if not m: return None
    a, b, y = m.groups(); d, mo = (a, b) if a.isdigit() else (b, a)
    return "%s-%02d-%02d" % (y, MONTHS[mo.lower()], int(d)) if mo.lower() in MONTHS else None

def code(s):
    m = re.search(r"\{\{\s*(?:fb|fb-rt|fbu|fb-big)\s*\|\s*([A-Z]{3})", s, flags=re.I)
    return m.group(1).upper() if m else None

def person(chunk):
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", chunk)
    if m: return re.sub(r"\s*\(.*?\)$", "", m.group(1).strip())
    return strip(re.sub(r"\{\{.*?\}\}", "", chunk))

def goals(field):
    out = []
    for part in re.split(r"<br\s*/?>|\n", field or ""):
        if not part.strip(): continue
        name = person(part)
        for kind, args in re.findall(r"\{\{\s*(goal|og)\s*((?:\|[^}]*)?)\}\}", part, flags=re.I):
            args = [a.strip() for a in args.split("|")[1:]]
            if kind.lower() == "og": out += [[name, a.rstrip("'′"), "og"] for a in args if a]; continue
            cur = None
            for a in args:
                if re.match(r"^\d+(\+\d+)?['′]?$", a):
                    if cur: out.append(cur)
                    cur = [name, a.rstrip("'′"), ""]
                elif a and cur: cur[2] = "p" if a.lower().startswith("pen") else "og" if a.lower().startswith("o") else ""
            if cur: out.append(cur)
    return out

def shootout(field):
    out = []
    for part in re.split(r"<br\s*/?>|\n", field or ""):
        k = re.search(r"\{\{\s*(pengoal|penmiss)", part, flags=re.I)
        if k: out.append([person(part), 1 if k.group(1).lower() == "pengoal" else 0])
    return out

def boxes(name):
    txt = open(D + name + ".txt", encoding="utf-8").read(); out = []
    for box in re.split(r"\{\{\s*(?:#invoke:\s*)?football ?box(?:\s*\|\s*main)?(?=\s*\n|\s*\|)", txt, flags=re.I)[1:]:
        F, key, depth = {}, None, 0
        for line in box.split("\n"):
            if line.strip().startswith("}}") and depth <= 0: break
            m = re.match(r"^\s*\|\s*([a-z0-9_]+)\s*=(.*)$", line)
            if m: key = m.group(1).lower(); F[key] = m.group(2).strip()
            elif key and line.strip(): F[key] += "\n" + line.strip()
        a, b = code(F.get("team1", "")), code(F.get("team2", ""))
        sc = re.search(r"(\d+)\s*[–-]\s*(\d+)", strip(re.sub(r"\{\{\s*score link\s*\|[^|}]*\|([^}]*)\}\}", r"\1", F.get("score", ""), flags=re.I)))
        if not (a and b and sc): continue
        g = dict(d=date(F.get("date", "")), t1=CODES.get(a, a), t2=CODES.get(b, b), s1=int(sc.group(1)), s2=int(sc.group(2)),
                 g1=goals(F.get("goals1")), g2=goals(F.get("goals2")), aet=F.get("aet", "").strip().lower() in ("yes", "y", "1") or "a.e.t" in F.get("score", ""),
                 p1=shootout(F.get("penalties1")), p2=shootout(F.get("penalties2")), ground=strip(F.get("stadium", "")), city=strip(F.get("location", "")),
                 att=re.sub(r"[^\d]", "", strip(F.get("attendance", ""))), ref=strip(F.get("referee", "")))
        ps = re.search(r"(\d+)\s*[–-]\s*(\d+)", strip(re.sub(r"\{\{\s*score link\s*\|[^|}]*\|([^}]*)\}\}", r"\1", F.get("penaltyscore", ""), flags=re.I)))
        if ps: g["ps"] = (int(ps.group(1)), int(ps.group(2)))
        out.append(g)
    return out

def table(name):
    """The group table as Wikipedia orders it: [(team, w, d, l, gf, ga)], or None if the article has no table of its own."""
    txt = open(D + name + ".txt", encoding="utf-8").read()
    m = re.search(r"\{\{\s*#invoke:\s*sports table(.*?)\n\}\}", txt, flags=re.I | re.S)
    if not m: return None
    t = m.group(1); P = dict(re.findall(r"\|\s*([a-zA-Z0-9_]+)\s*=\s*([^|\n]*)", t))
    order = [c.strip() for c in P["team_order"].split(",")] if "team_order" in P else [P[k] for k in sorted((k for k in P if re.match(r"team\d+$", k)), key=lambda k: int(k[4:]))]
    rows = []
    for c in order:
        c = c.strip().upper()
        rows.append((CODES.get(c, c), int(P.get("win_" + c, 0) or 0), int(P.get("draw_" + c, 0) or 0), int(P.get("loss_" + c, 0) or 0), int(P.get("gf_" + c, 0) or 0), int(P.get("ga_" + c, 0) or 0)))
    return rows

def standings(games, pts):
    T = {}
    for g in games:
        for n, f, a in ((g["t1"], g["s1"], g["s2"]), (g["t2"], g["s2"], g["s1"])):
            t = T.setdefault(n, dict(n=n, p=0, w=0, d=0, l=0, f=0, a=0))
            t["p"] += 1; t["f"] += f; t["a"] += a
            t["w" if f > a else "d" if f == a else "l"] += 1
    for t in T.values(): t["pts"] = t["w"] * pts + t["d"]
    return T
