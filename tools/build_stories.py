#!/usr/bin/env python3
"""Write the big-match and campaign pages (site/matches/<slug>/, site/campaigns/<slug>/) as plain HTML, so they can be shared with a
proper title and preview. Page chrome comes from site/kits/index.html; results come from the archive and are checked against it here.
Run from the repo root after build_archive.py: python3 tools/build_stories.py"""
import html, json, os, re
E = html.escape
M = json.load(open("site/history/matches.json", encoding="utf-8"))
P = {p["name"]: p["slug"] for p in json.load(open("site/history/players.json", encoding="utf-8"))}
ROW = {x["d"]: x for x in M}
ORIGIN = "https://irelandfootball.wiki"
KITS = open("site/kits/index.html", encoding="utf-8").read()
FOOT_END = KITS.index("</footer>")

def dt(d, year=True):
    y, m, day = d.split("-")
    return f"{int(day)} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m)-1]}" + (f" {y}" if year else "")
def who(n, shown=None):
    assert n in P, n
    return f'<a href="/player/?p={P[n]}">{E(shown or n)}</a>'
def team(n):
    return f'<span data-club="{E("Rep. Of Ireland" if n == "Ireland" else n)}">{E(n)}</span>'
def ext(u, t):
    return f'<a class="btn" href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a>'
def src(u, t):
    return f'<a href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a>'
def table(head, rows):
    h = "".join(f'<th{" class=n" if c[1] else ""}>{c[0]}</th>' for c in head)
    return f'<table class="mu"><thead><tr>{h}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
def tr(cells, head, cls=""):
    c = "".join(f'<td{" class=n" if head[i][1] else ""}>{x}</td>' for i, x in enumerate(cells))
    return f'<tr{f" class={cls}" if cls else ""}>{c}</tr>'
def score(r):
    return f"{r['gf']}–{r['ga']}" + (" (won on penalties)" if r.get("pw") == 1 else " (lost on penalties)" if r.get("pw") == 0 else "")
def names(r):
    out = []
    for s in r.get("sc", []):
        out.append(f"{s[0]} {s[1]}′" + (" (pen)" if "p" in s else "") if s[1] else s[0])
    return ", ".join(out)
def ire(r):
    """One archive game as Home v Away with Ireland's side right."""
    if r["h"] == -1: return f"{team(r['o'])} {r['ga']}–{r['gf']} {team('Ireland')}"
    return f"{team('Ireland')} {r['gf']}–{r['ga']} {team(r['o'])}"

def page(path, title, desc, nav, body, credit):
    head = KITS[:KITS.index("</head>")]
    head = re.sub(r"<title>.*?</title>", f"<title>{E(title)}</title>", head, count=1, flags=re.S)
    url = ORIGIN + path
    og = f'<meta name="description" content="{E(desc)}"><meta property="og:type" content="article"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{ORIGIN}/assets/crest.png"><meta name="twitter:card" content="summary"><link rel="canonical" href="{url}">\n'
    top = KITS[KITS.index("</head>"):KITS.index("<main")]
    top = re.sub(r'<div class="from" id="from">.*?</div>', f'<div class="from" id="from">History<span>{E(nav)}</span></div>', top, flags=re.S)
    foot = KITS[KITS.index("</main>"):FOOT_END]
    out = head + og + top + '<main id="main-content" tabindex="-1">\n' + body + "\n" + foot + " " + credit + "</footer>\n</div>\n" + '''<script src="/mu.js"></script>
<script>
(function(){
MU.nav('Results'); MU.checked("archive",document.getElementById("stamp"),"Archive built");
document.querySelectorAll("[data-club]").forEach(function(e){e.innerHTML=MU.club(e.getAttribute("data-club"),14)});
})();
</script></body></html>
'''
    d = "site" + path
    os.makedirs(d, exist_ok=True)
    open(d + "index.html", "w", encoding="utf-8").write(out)

# ---------------------------------------------------------------------------------------------------------------- Romania 1990
r = ROW["1990-06-25"]
assert (r["o"], r["gf"], r["ga"], r["pw"]) == ("Romania", 0, 0, 1)
WC = [x for x in M if x["c"] == "WC" and x["d"].startswith("1990")]
assert [(x["o"], x["gf"], x["ga"]) for x in WC] == [("England", 1, 1), ("Egypt", 0, 0), ("Netherlands", 1, 1), ("Romania", 0, 0), ("Italy", 0, 1)]
assert not [x for x in M if x["c"] == "WC" and x["d"] < "1990"]
KICKS = [("Romania", "Gheorghe Hagi", 1), ("Ireland", "Kevin Sheedy", 1), ("Romania", "Dănuț Lupu", 1), ("Ireland", "Ray Houghton", 1), ("Romania", "Iosif Rotariu", 1), ("Ireland", "Andy Townsend", 1), ("Romania", "Ioan Lupescu", 1), ("Ireland", "Tony Cascarino", 1), ("Romania", "Daniel Timofte", 0), ("Ireland", "David O'Leary", 1)]
H = [("Kick", 1), ("Team", 0), ("Taker", 0), ("Result", 0), ("Ireland–Romania", 1)]
ie = ro = 0; rows = []
for i, (t, n, ok) in enumerate(KICKS, 1):
    if t == "Ireland": ie += ok
    else: ro += ok
    res = "Scored" if ok else "Saved by " + who("Packie Bonner")
    shown = who(n, n.replace("'", "’")) if t == "Ireland" else E(n)
    if i == 10: res = "Scored. Ireland are through"
    rows.append(tr([i, team(t), shown, res, f"{ie}–{ro}"], H, "key" if i >= 9 else ""))
assert (ie, ro) == (5, 4)
H2 = [("Date", 0), ("Round", 0), ("Game", 0), ("Where", 0), ("Scorers", 0)]
RND = ["Group", "Group", "Group", "Last 16", "Quarter-final"]
gm = "".join(tr([dt(x["d"]), RND[i], ire(x) + (" (5–4 on penalties)" if x.get("pw") == 1 else ""), E(x["city"]), E(names(x)) or ("Salvatore Schillaci for Italy" if x["o"] == "Italy" else "None")], H2, "key" if x["d"] == r["d"] else "") for i, x in enumerate(WC))
body = f'''<div class="sheet story">
  <h2>World Cup 1990, last 16</h2>
  <div class="big">{team("Ireland")} 0–0 {team("Romania")}</div>
  <p><b>Ireland won 5–4 on penalties, after extra time.</b><br>Monday 25 June 1990, 17:00 local time. {E("Stadio Luigi Ferraris, Genoa")}. Crowd 31818. Referee José Roberto Wright (Brazil). Manager <a href="/manager/?m={r["ms"]}">Jack Charlton</a>.</p>
  <p>This was Ireland’s first World Cup. Beating Romania put them into the quarter-finals at the first attempt, and they got there without winning a game in 90 minutes: three group draws, two goals, then this 0–0. The game extended their unbeaten run to 17 matches, then a record.</p>
  <p class="watchl">{ext("https://www.fifa.com/en/watch/7yZJ3FzhyDjrs1mwUQlFHg", "Watch FIFA’s highlights")}{ext("https://www.youtube.com/watch?v=A0LR0fmN3gM", "Bonner’s save and O’Leary’s kick, RTÉ")}</p>
</div>
<div class="sheet"><h2>The shoot-out, kick by kick</h2>
{table(H, rows)}
<p class="sub" style="margin:10px 0 0">Romania kicked first. FIFA’s full shoot-out is on {src("https://www.plus.fifa.com/en/content/republic-of-ireland-v-romania-round-of-16-1990-fifa-world-cup-italytm-penalty-shoot-out/55cdb9d0-dfac-4181-b6f2-3fdf176983b0", "FIFA+")}, which now opens on DAZN.</p>
</div>
<div class="two" style="margin-top:12px">
<div class="sheet" style="margin-top:0"><h2>Daniel Timofte</h2><p>Romania’s midfielder came on after 98 minutes, in place of Ioan Sabău, and took their fifth kick with the shoot-out level at 4–4. {who("Packie Bonner")} saved it, the only kick of the ten that did not go in.</p></div>
<div class="sheet" style="margin-top:0"><h2>David O’Leary</h2><p>The Arsenal defender did not get on the pitch in the group games. He replaced Steve Staunton after 94 minutes and, by his own account, took number five because it was the last number left. His kick sent Ireland through. As RTÉ’s George Hamilton put it, “The nation holds its breath.”</p><p><a href="/player/?p={P["David O'Leary"]}">O’Leary’s profile</a></p></div>
</div>
<div class="sheet"><h2>Line-ups</h2><div class="two">
<div><h3>{team("Ireland")}</h3><p>{who("Packie Bonner")}; {who("Chris Morris")}, {who("Mick McCarthy")} (captain), {who("Paul McGrath")}, {who("Kevin Moran")}, {who("Steve Staunton")}; {who("Ray Houghton")}, {who("Andy Townsend")}, {who("Kevin Sheedy")}; {who("John Aldridge")}, {who("Niall Quinn")}.</p><p class="sub">Substitutes used: {who("Tony Cascarino")} for Aldridge (22′), {who("David O'Leary", "David O’Leary")} for Staunton (94′). Booked: Aldridge, McGrath.</p></div>
<div><h3>{team("Romania")}</h3><p>Silviu Lung (captain); Gheorghe Popescu, Ioan Andone, Ioan Lupescu; Mircea Rednic, Ioan Sabău, Gheorghe Hagi, Iosif Rotariu, Michael Klein; Gavril Balint, Florin Răducioiu.</p><p class="sub">Substitutes used: Dănuț Lupu for Răducioiu (74′), Daniel Timofte for Sabău (98′). Booked: Hagi, Lupu.</p></div>
</div></div>
<div class="sheet"><h2>Ireland’s Italia ’90</h2>{table(H2, [gm])}
<p class="sub" style="margin:10px 0 0">The quarter-final against Italy was in Rome on 30 June. <a href="/opponent/?o=romania">Every game against Romania</a> · <a href="/results/">All results</a></p></div>'''
credit = "This page: " + src("https://en.wikipedia.org/wiki/1990_FIFA_World_Cup_knockout_stage", "Wikipedia") + " (CC BY-SA), " + src("https://www.rte.ie/archives/2015/0624/710356-football-ireland-beat-romania-at-italia-90/", "RTÉ Archives") + ", " + src("https://www.skysports.com/football/news/9889945/ireland-s-world-cup-joy-david-o-leary-recalls-his-penalty-v-romania", "Sky Sports") + "."
page("/matches/ireland-romania-1990/", "Ireland 0–0 Romania, 5–4 on penalties: Italia ’90", "Every kick of the shoot-out in Genoa: Bonner’s save from Timofte, O’Leary’s winner, and Ireland’s first World Cup quarter-final.", "Great days", body, credit)

# ---------------------------------------------------------------------------------------------------------------------- Euro 88
G7 = [("10 Sep 1986", "Belgium", 2, 2, "Ireland"), ("10 Sep 1986", "Scotland", 0, 0, "Bulgaria"), ("14 Oct 1986", "Luxembourg", 0, 6, "Belgium"), ("15 Oct 1986", "Ireland", 0, 0, "Scotland"), ("12 Nov 1986", "Scotland", 3, 0, "Luxembourg"), ("19 Nov 1986", "Belgium", 1, 1, "Bulgaria"), ("18 Feb 1987", "Scotland", 0, 1, "Ireland"), ("1 Apr 1987", "Bulgaria", 2, 1, "Ireland"), ("1 Apr 1987", "Belgium", 4, 1, "Scotland"), ("29 Apr 1987", "Ireland", 0, 0, "Belgium"), ("30 Apr 1987", "Luxembourg", 1, 4, "Bulgaria"), ("20 May 1987", "Bulgaria", 3, 0, "Luxembourg"), ("28 May 1987", "Luxembourg", 0, 2, "Ireland"), ("9 Sep 1987", "Ireland", 2, 1, "Luxembourg"), ("23 Sep 1987", "Bulgaria", 2, 0, "Belgium"), ("14 Oct 1987", "Ireland", 2, 0, "Bulgaria"), ("14 Oct 1987", "Scotland", 2, 0, "Belgium"), ("11 Nov 1987", "Belgium", 3, 0, "Luxembourg"), ("11 Nov 1987", "Bulgaria", 0, 1, "Scotland"), ("2 Dec 1987", "Luxembourg", 0, 0, "Scotland")]
def standings(games):
    T = {}
    for _, a, x, y, b in games:
        for n, f, g in ((a, x, y), (b, y, x)):
            t = T.setdefault(n, dict(n=n, p=0, w=0, d=0, l=0, f=0, a=0, pts=0))
            t["p"] += 1; t["f"] += f; t["a"] += g
            if f > g: t["w"] += 1; t["pts"] += 2
            elif f == g: t["d"] += 1; t["pts"] += 1
            else: t["l"] += 1
    return sorted(T.values(), key=lambda t: (-t["pts"], -(t["f"] - t["a"]), -t["f"]))
S7 = standings(G7)
assert [(t["n"], t["pts"], t["f"], t["a"]) for t in S7] == [("Ireland", 11, 10, 5), ("Bulgaria", 10, 12, 6), ("Belgium", 9, 16, 8), ("Scotland", 9, 7, 5), ("Luxembourg", 1, 2, 23)]
before = standings([g for g in G7 if g[0] not in ("11 Nov 1987", "2 Dec 1987")] + [g for g in G7 if g[0] == "11 Nov 1987" and g[1] == "Belgium"])
assert [(t["n"], t["p"], t["pts"], t["f"] - t["a"]) for t in before[:2]] == [("Ireland", 8, 11, 5), ("Bulgaria", 7, 10, 7)]
ifdraw = standings([g if not (g[0] == "11 Nov 1987" and g[1] == "Bulgaria") else (g[0], g[1], 0, 0, g[4]) for g in G7])
assert ifdraw[0]["n"] == "Bulgaria" and (ifdraw[0]["pts"], ifdraw[1]["pts"]) == (11, 11)
for x in M:   # Ireland's games in the list above must agree with the archive
    if "1986-09-01" <= x["d"] <= "1987-12-31" and x["c"] == "ECQ":
        assert any(g[2:4] in ((x["gf"], x["ga"]), (x["ga"], x["gf"])) and x["o"] in (g[1], g[4]) and "Ireland" in (g[1], g[4]) for g in G7), x
def stable(S, hl="Ireland"):
    H = [("Team", 0), ("P", 1), ("W", 1), ("D", 1), ("L", 1), ("F", 1), ("A", 1), ("Pts", 1)]
    return table(H, [tr([team(t["n"]), t["p"], t["w"], t["d"], t["l"], t["f"], t["a"], t["pts"]], H, "key" if t["n"] == hl else "") for t in S])
HQ = [("Date", 0), ("Game", 0), ("", 0)]
WHY = {("14 Oct 1987", "Ireland"): "Ireland’s last game. Second-half goals from McGrath and Moran, then a month’s wait.", ("11 Nov 1987", "Bulgaria"): "Mackay, 86′. Scotland could not qualify; their win sent Ireland through.", ("1 Apr 1987", "Bulgaria"): "Ireland’s only defeat, two Tanev goals, the second a late penalty.", ("18 Feb 1987", "Scotland"): "Lawrenson’s early goal won it at Hampden.", ("23 Sep 1987", "Bulgaria"): "Belgium, the group favourites, fell away. They did not beat Ireland or Bulgaria."}
gq = []
for g in G7:
    us = "Ireland" in (g[1], g[4]); k = (g[0], g[1]); note = WHY.get(k, "")
    if not us: note = '<span class="tagn">Not an Ireland game</span>' + note
    gq.append(tr([g[0], f"{team(g[1])} {g[2]}–{g[3]} {team(g[4])}", note], HQ, "key" if k in (("14 Oct 1987", "Ireland"), ("11 Nov 1987", "Bulgaria")) else "" if us else "not"))
F2 = [("12 Jun 1988", "England", 0, 1, "Ireland"), ("12 Jun 1988", "Soviet Union", 1, 0, "Netherlands"), ("15 Jun 1988", "Ireland", 1, 1, "Soviet Union"), ("15 Jun 1988", "England", 1, 3, "Netherlands"), ("18 Jun 1988", "England", 1, 3, "Soviet Union"), ("18 Jun 1988", "Ireland", 0, 1, "Netherlands")]
S2 = standings(F2)
assert [(t["n"], t["pts"], t["f"], t["a"]) for t in S2] == [("Soviet Union", 5, 5, 2), ("Netherlands", 4, 4, 2), ("Ireland", 3, 2, 2), ("England", 0, 2, 7)]
dr = standings(F2[:-1] + [("18 Jun 1988", "Ireland", 0, 0, "Netherlands")])
assert (dr[1]["n"], dr[1]["pts"], dr[2]["n"], dr[2]["pts"]) == ("Ireland", 4, "Netherlands", 3)
for d, o in (("1988-06-12", "England"), ("1988-06-15", "Soviet Union"), ("1988-06-18", "Netherlands")): assert ROW[d]["o"] == o and ROW[d]["c"] == "EC"
HF = [("Date", 0), ("Game", 0), ("Where", 0), ("Ireland’s scorer", 0), ("", 0)]
fin = "".join(tr([dt(d), ire(ROW[d]), E(ROW[d]["city"]), E(names(ROW[d])) or "None", n], HF, "key" if d == "1988-06-12" else "") for d, n in (("1988-06-12", "Houghton scored the winner in the sixth minute. Ireland’s first game at a major finals."), ("1988-06-15", "Whelan’s goal, Protasov levelled after 74 minutes."), ("1988-06-18", "A draw would have sent Ireland to the semi-finals. Kieft scored after 82 minutes.")))
SQ = [(1, "GK", "Packie Bonner", "Celtic", 23), (2, "DF", "Chris Morris", "Celtic", 5), (3, "DF", "Chris Hughton", "Tottenham Hotspur", 36), (4, "DF", "Mick McCarthy", "Celtic", 27), (5, "DF", "Kevin Moran", "Manchester United", 36), (6, "MF", "Ronnie Whelan", "Liverpool", 26), (7, "MF", "Paul McGrath", "Manchester United", 23), (8, "MF", "Ray Houghton", "Liverpool", 15), (9, "FW", "John Aldridge", "Liverpool", 15), (10, "FW", "Frank Stapleton", "Derby County", 63), (11, "MF", "Tony Galvin", "Sheffield Wednesday", 24), (12, "FW", "Tony Cascarino", "Millwall", 5), (13, "MF", "Liam O'Brien", "Manchester United", 6), (14, "FW", "David Kelly", "Walsall", 3), (15, "MF", "Kevin Sheedy", "Everton", 13), (16, "GK", "Gerry Peyton", "Bournemouth", 24), (17, "FW", "John Byrne", "Le Havre", 14), (18, "MF", "John Sheridan", "Leeds United", 4), (19, "DF", "John Anderson", "Newcastle United", 15), (20, "FW", "Niall Quinn", "Arsenal", 9)]
HS = [("No.", 1), ("Pos", 0), ("Player", 0), ("Club", 0), ("Caps before", 1)]
squad = [tr([n, pos, who(name, name.replace("'", "’")) + (" (captain)" if name == "Frank Stapleton" else ""), E(c), caps], HS) for n, pos, name, c, caps in SQ]
body = f'''<div class="sheet story">
  <h2>Euro ’88</h2>
  <div class="big">Ireland’s first finals, decided in a game they did not play</div>
  <p>Ireland finished their qualifying group on 14 October 1987, top on 11 points, and could do nothing more. Bulgaria had a game left, at home to Scotland in Sofia, and a draw would have put Bulgaria through on goal difference.</p>
  <p>On 11 November 1987 {team("Scotland")}, who could no longer qualify, won 1–0. Gary Mackay, a substitute, scored four minutes from time. Seven months later, in Ireland’s first game at a major finals, {who("Ray Houghton")} scored after six minutes to beat {team("England")}. <a href="/manager/?m=jack-charlton">Jack Charlton</a> was the manager.</p>
  <p class="watchl">{ext("https://www.uefa.com/uefaeuro/match/1378--bulgaria-vs-scotland/", "Bulgaria v Scotland, UEFA")}{ext("https://www.uefa.com/uefaeuro/match/13/", "England v Ireland, UEFA")}</p>
</div>
<div class="sheet"><h2>Qualifying Group 7, final table</h2>{stable(S7)}<p class="sub" style="margin:10px 0 0">Two points for a win. Before the Sofia game, Ireland had 11 points from 8 games and a goal difference of +5. Bulgaria had 10 points from 7 and +7.</p></div>
<div class="sheet"><h2>Every game in the group</h2>{table(HQ, gq)}<p class="sub" style="margin:10px 0 0">Highlighted: the two games that settled it.</p></div>
<div class="sheet"><h2>The finals, West Germany</h2>{table(HF, [fin])}<h3 style="margin-top:16px">Group 2, final table</h3>{stable(S2)}<p class="sub" style="margin:10px 0 0">Ireland went out by one point. They were welcomed home by about 200000 people.</p></div>
<div class="sheet"><h2>The shirts</h2><div class="kit2"><figure><img src="/assets/kits/1988-home.png" alt="Euro 1988 home shirt" loading="lazy"><figcaption><b>Home</b></figcaption></figure><figure><img src="/assets/kits/1988-away.png" alt="Euro 1988 away shirt" loading="lazy"><figcaption><b>Away</b></figcaption></figure></div><p class="sub"><a href="/kits/">All kits and crests</a></p></div>
<div class="sheet"><h2>The squad</h2>{table(HS, squad)}<p class="sub" style="margin:10px 0 0">Caps as they stood when the tournament began.</p></div>'''
credit = "This page: " + src("https://en.wikipedia.org/wiki/UEFA_Euro_1988_qualifying_Group_7", "Wikipedia group, finals and squad articles") + " (CC BY-SA)."
page("/campaigns/euro-1988/", "Euro ’88: how Ireland got there", "The qualifying table, the Scotland win in Sofia that sent Ireland through, Houghton’s goal against England, the squad and the shirts.", "Campaigns", body, credit)
print("ok")
