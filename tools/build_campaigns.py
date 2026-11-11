#!/usr/bin/env python3
"""Campaign pages for every major finals Ireland reached after Euro ’88 (which build_stories.py writes by hand):
site/campaigns/<slug>/. Tables, results, scorers and squads come from Wikipedia's tournament articles (tools/data/campaigns/,
CC BY-SA, fetched by fetch_sources.py); every Ireland game is checked against the archive and every group table against the
games in it. Run from the repo root after build_archive.py and build_reports.py: python3 tools/build_campaigns.py"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from story_lib import *
from campaign_data import boxes, table as wtable, standings, CODES, D as CD

REP = json.load(open("site/history/reports.json", encoding="utf-8"))
_P = json.load(open("site/history/players.json", encoding="utf-8"))
NAMES = {p["name"].lower(): p for p in _P}
def wkey(s): return re.sub(r"[,.]", "", s.replace("_", " ")).lower().strip()
BY_WIKI = {wkey(p["wiki"]): p for p in _P if p.get("wiki")}
STORIES = json.load(open("tools/data/stories.json", encoding="utf-8"))
WIKI = "https://en.wikipedia.org/wiki/"

def arch(b):
    """The archive row for one of Ireland's games in a Wikipedia box, checked: same opponent and score, date within a day."""
    opp = b["t2"] if b["t1"] == "Ireland" else b["t1"]
    gf, ga = (b["s1"], b["s2"]) if b["t1"] == "Ireland" else (b["s2"], b["s1"])
    for k in (0, -1, 1):
        d = (datetime.date.fromisoformat(b["d"]) + datetime.timedelta(days=k)).isoformat()
        r = ROW.get(d)
        if r and r["o"] == opp:
            assert (r["gf"], r["ga"]) == (gf, ga), (b, r)
            return r
    raise AssertionError(("not in the archive", b))

def ire_games(name):
    return [arch(b) | {"_box": b} for b in boxes(name) if "Ireland" in (b["t1"], b["t2"])]

def scorers(r):
    """Ireland's goals and the other side's, from the match report data when it agrees with the archive, else the archive."""
    g = REP.get(r["d"], {}).get("g")
    if g:
        us = ", ".join(f'{x[1]} {x[2]}′' + (" (pen)" if x[3] == "p" else " (og)" if x[3] == "og" else "") for x in g if x[0])
        them = ", ".join(f'{x[1]} {x[2]}′' + (" (pen)" if x[3] == "p" else " (og)" if x[3] == "og" else "") for x in g if not x[0])
        return us, them
    return ", ".join(f"{s[0]} {s[1]}′" if s[1] else s[0] for s in r.get("sc", [])), ""

def game_row(r, note=""):
    us, them = scorers(r)
    link = f'<a href="/report/?d={r["d"]}">{ire(r)}</a>'
    pens = " (won on penalties)" if r.get("pw") == 1 else " (lost on penalties)" if r.get("pw") == 0 else ""
    bits = [E(r["city"])] + ([f"Ireland: {E(us)}"] if us else []) + ([f"{E(r['o'])}: {E(them)}"] if them else []) + ([note] if note else [])
    return tr([dt(r["d"]), link + pens + f'<span class="tagn">{" · ".join(bits)}</span>'], HG)
HG = [("Date", 0), ("Game", 0)]

def group_table(name, pts):
    B = boxes(name); T = standings(B, pts); W = wtable(name)
    if W:
        for n, w, d, l, f, a in W: assert (T[n]["w"], T[n]["d"], T[n]["l"], T[n]["f"], T[n]["a"]) == (w, d, l, f, a), (name, n)
        order = [x[0] for x in W]
    else:
        S = sorted(T.values(), key=lambda t: (-t["pts"], -(t["f"] - t["a"]), -t["f"]))
        assert len({t["pts"] for t in S}) == len(S), ("tied on points; needs Wikipedia's order", name)
        order = [t["n"] for t in S]
    H = [("Team", 0), ("P", 1), ("W", 1), ("D", 1), ("L", 1), ("F", 1), ("A", 1), ("Pts", 1)]
    rows = [tr([team(n), T[n]["p"], T[n]["w"], T[n]["d"], T[n]["l"], T[n]["f"], T[n]["a"], T[n]["pts"]], H, "key" if n == "Ireland" else "") for n in order]
    return table(H, rows), order, T

def squad(name):
    txt = open(CD + name + ".txt", encoding="utf-8").read()
    s = re.search(r"===\s*Republic of Ireland\s*===", txt).end(); e = re.search(r"\n===?[^=]", txt[s:]).start() + s
    H = [("No.", 1), ("Pos", 0), ("Player", 0), ("Club", 0), ("Caps", 1)]; rows = []
    for t in re.findall(r"\{\{nat fs (?:g )?player\s*\|(.*?)\}\}\s*$", txt[s:e], flags=re.M):
        F = dict(re.findall(r"(\w+)\s*=\s*((?:\[\[[^\]]*\]\]|\{\{[^}]*\}\}|[^|])*)", t))
        m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", F.get("name", ""))
        nm = (m.group(2) or m.group(1)) if m else F.get("name", "").strip()
        nm = re.sub(r"\s*\(.*?\)$", "", nm)
        p = (BY_WIKI.get(wkey(m.group(1))) if m else None) or NAMES.get(nm.lower())
        cl = re.search(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]", F.get("club", ""))
        club = (cl.group(2) or cl.group(1)) if cl else F.get("club", "").strip()
        cap = " (captain)" if "captain" in F.get("other", "").lower() else ""
        rows.append(tr([F.get("no", "").strip(), F.get("pos", "").strip(), (f'<a href="/player/?p={p["slug"]}">{E(nm)}</a>' if p else E(nm)) + cap, E(club), F.get("caps", "").strip()], H))
    assert len(rows) >= 22, (name, len(rows))
    return table(H, rows), len(rows)

def kits(y, label):
    return (f'<div class="sheet"><h2>The shirts</h2><div class="kit2"><figure><img src="/assets/kits/{y}-home.png" alt="{label} home shirt" loading="lazy"><figcaption><b>Home</b></figcaption></figure>'
            f'<figure><img src="/assets/kits/{y}-away.png" alt="{label} away shirt" loading="lazy"><figcaption><b>Away</b></figcaption></figure></div><p class="sub"><a href="/kits/">All kits and crests</a></p></div>')

def build(c):
    q_tab, q_order, q_T = group_table(c["q"], c["qpts"])
    qg = ire_games(c["q"]); po = ire_games(c["po"]) if c.get("po") else []
    g_tab, g_order, g_T = group_table(c["g"], c["gpts"])
    fg = ire_games(c["g"]); ko = ire_games(c["ko"]) if c.get("ko") else []
    for x in fg + ko: assert x["c"] == c["comp"], x
    for x in qg + po: assert x["c"] == c["comp"] + "Q", x
    sq, nsq = squad(c["sq"])
    pos = q_order.index("Ireland") + 1; fpos = g_order.index("Ireland") + 1
    assert (pos, fpos) == c["pos"], (c["slug"], pos, fpos)
    body = f'''<div class="sheet story">
  <h2>{E(c["name"])}</h2>
  <div class="big">{E(c["head"])}</div>
  {c["story"]}
  <p class="watchl">{"".join(ext(WIKI + u, t) for u, t in c["links"])}</p>
</div>
<div class="sheet"><h2>{E(c["qname"])}, final table</h2>{q_tab}<p class="sub" style="margin:10px 0 0">{c["qnote"]}</p></div>
<div class="sheet"><h2>Ireland’s qualifying games</h2>{table(HG, [game_row(r) for r in qg])}</div>'''
    if po:
        agg = (sum(r["gf"] for r in po), sum(r["ga"] for r in po))
        body += f'<div class="sheet"><h2>Play-off</h2>{table(HG, [game_row(r) for r in po])}<p class="sub" style="margin:10px 0 0">Ireland won {agg[0]}–{agg[1]} on aggregate.</p></div>'
        assert agg[0] > agg[1]
    body += f'''<div class="sheet"><h2>The finals, {E(c["host"])}</h2>{table(HG, [game_row(r) for r in fg + ko])}<h3 style="margin-top:16px">{E(c["gname"])}, final table</h3>{g_tab}<p class="sub" style="margin:10px 0 0">{c["gnote"]}</p></div>
{kits(c["y"], c["name"])}
<div class="sheet"><h2>The squad</h2>{sq}<p class="sub" style="margin:10px 0 0">Caps as they stood when the tournament began. Manager: <a href="/manager/?m={c["mgr"][0]}">{E(c["mgr"][1])}</a>.</p></div>'''
    credit = "This page: Wikipedia, " + ", ".join(src(WIKI + u, t) for u, t in c["credit"]) + " (CC BY-SA)."
    page(f'/campaigns/{c["slug"]}/', c["title"], c["desc"], "Campaigns", body, credit)
    return dict(q=qg, po=po, f=fg, ko=ko, T=q_T, nsq=nsq)

def city(d): return E(ROW[d]["city"])
C = [
 dict(slug="world-cup-1990", y=1990, comp="WC", name="Italia ’90", host="Italy", title="Italia ’90: Ireland’s first World Cup",
      desc="Second behind Spain in qualifying, three draws in the group, Genoa and the shoot-out, and a quarter-final against the hosts in Rome.",
      head="Ireland’s first World Cup: five games, one defeat, a quarter-final in Rome",
      q="wc1990_q", qpts=2, qname="Qualifying Group 6", g="wc1990_g", gpts=2, gname="Group F", ko="wc1990_ko", sq="wc1990_sq", pos=(2, 2), mgr=("jack-charlton", "Jack Charlton"),
      story=f'''<p>Ireland qualified second in Group 6, a point behind {team("Spain")}, with five wins in eight games and two goals conceded. Their only defeat was in {city("1988-11-16")}.</p>
  <p>In Italy they drew all three group games, with {team("England")}, {team("Egypt")} and the {team("Netherlands")}. Ireland and the Netherlands finished level on everything, and lots were drawn for second place. Ireland went to {city("1990-06-25")} and <a href="/matches/ireland-romania-1990/">beat Romania on penalties</a>. On 30 June they lost 1–0 to {team("Italy")} in {city("1990-06-30")}; Salvatore Schillaci scored.</p>''',
      qnote="Two points for a win. Spain and Ireland both qualified.", gnote="Two points for a win. Ireland and the Netherlands finished level on every count; lots decided second and third, and both went through.",
      links=[("1990_FIFA_World_Cup", "1990 World Cup, Wikipedia")], credit=[("1990_FIFA_World_Cup_qualification_–_UEFA_Group_6", "qualifying group"), ("1990_FIFA_World_Cup_Group_F", "Group F"), ("1990_FIFA_World_Cup_knockout_stage", "knockout stage"), ("1990_FIFA_World_Cup_squads", "squads")]),
 dict(slug="world-cup-1994", y=1994, comp="WC", name="USA ’94", host="United States", title="USA ’94: Ireland at the World Cup",
      desc="Through on goals scored after a draw in Belfast, Houghton’s goal against Italy, and a last-16 defeat to the Netherlands in Orlando.",
      head="Through on goals scored, then Houghton’s goal beat Italy",
      q="wc1994_q", qpts=2, qname="Qualifying Group 3", g="wc1994_g", gpts=3, gname="Group E", ko="wc1994_ko", sq="wc1994_sq", pos=(2, 2), mgr=("jack-charlton", "Jack Charlton"),
      story=f'''<p>Ireland finished Group 3 level with {team("Denmark")} on 18 points and the same goal difference, and went through on goals scored, 19 to 15. {team("Spain")} won the group. Ireland’s last game was in {city("1993-11-17")} on 17 November 1993: {team("Northern Ireland")} led through Jimmy Quinn, and {who("Alan McLoughlin")} equalised soon after.</p>
  <p>At the finals {who("Ray Houghton")} scored the only goal against {team("Italy")} at Giants Stadium. {team("Mexico")} won 2–1 in {city("1994-06-24")}, and a goalless draw with {team("Norway")} left all four teams in Group E on four points. Ireland finished second; Norway went out on goals scored. The {team("Netherlands")} won the last-16 game 2–0 in {city("1994-07-04")}.</p>''',
      qnote="Two points for a win. Ireland and Denmark were level on points and goal difference; Ireland scored more goals. The top two qualified.", gnote="Three points for a win, the first World Cup to use them. All four teams finished on four points and a goal difference of zero. Ireland were placed above Italy because they won the game between them.",
      links=[("1994_FIFA_World_Cup", "1994 World Cup, Wikipedia")], credit=[("1994_FIFA_World_Cup_qualification_–_UEFA_Group_3", "qualifying group"), ("1994_FIFA_World_Cup_Group_E", "Group E"), ("1994_FIFA_World_Cup_knockout_stage", "knockout stage"), ("1994_FIFA_World_Cup_squads", "squads")]),
 dict(slug="world-cup-2002", y=2002, comp="WC", name="World Cup 2002", host="Japan and South Korea", title="World Cup 2002: Ireland in Japan and Korea",
      desc="Unbeaten in qualifying, McAteer’s goal against the Netherlands, the play-off with Iran, Keane’s late goal against Germany and the shoot-out with Spain.",
      head="Unbeaten in qualifying, a stoppage-time goal against Germany, out on penalties to Spain",
      q="wc2002_q", qpts=3, qname="Qualifying Group 2", po="wc2002_po", g="wc2002_g", gpts=3, gname="Group E", ko="wc2002_ko", sq="wc2002_sq", pos=(2, 2), mgr=("mick-mccarthy", "Mick McCarthy"),
      story=f'''<p>Ireland went through qualifying unbeaten and finished level with {team("Portugal")} on 24 points, second on goal difference. {who("Jason McAteer")}’s goal beat the {team("Netherlands")} 1–0 in Dublin on 1 September 2001 and kept the Dutch out. A play-off with {team("Iran")} followed: 2–0 in Dublin, 1–0 to Iran in {city("2001-11-15")}.</p>
  <p>Before the finals {who("Roy Keane")} left the squad and was not replaced. In Japan, {who("Matt Holland")} scored in a 1–1 draw with {team("Cameroon")}, {who("Robbie Keane")} equalised against {team("Germany")} in stoppage time, and a 3–0 win over {team("Saudi Arabia")} put Ireland second in Group E. Against {team("Spain")} in {city("2002-06-16")}, Keane’s penalty in the 90th minute made it 1–1. Spain won the shoot-out 3–2.</p>''',
      qnote="Three points for a win. Portugal and Ireland were level on points; Portugal had the better goal difference. Second place meant a play-off, and Ireland drew Iran.", gnote="Three points for a win. The top two went through.",
      links=[("2002_FIFA_World_Cup", "2002 World Cup, Wikipedia")], credit=[("2002_FIFA_World_Cup_qualification_–_UEFA_Group_2", "qualifying group"), ("2002_FIFA_World_Cup_qualification_(UEFA–AFC_play-off)", "play-off"), ("2002_FIFA_World_Cup_Group_E", "Group E"), ("2002_FIFA_World_Cup_knockout_stage", "knockout stage"), ("2002_FIFA_World_Cup_squads", "squads")]),
 dict(slug="euro-2012", y=2012, comp="EC", name="Euro 2012", host="Poland", title="Euro 2012: Ireland in Poland",
      desc="Second behind Russia, 4–0 in Tallinn in the play-off, and three defeats at the finals in Poznań and Gdańsk.",
      head="Second in the group, 4–0 in Tallinn, three defeats in Poland",
      q="ec2012_q", qpts=3, qname="Qualifying Group B", po="ec2012_po", g="ec2012_g", gpts=3, gname="Group C", sq="ec2012_sq", pos=(2, 4), mgr=("giovanni-trapattoni", "Giovanni Trapattoni"),
      story=f'''<p>Ireland finished second in Group B, two points behind {team("Russia")}, and met {team("Estonia")} in a play-off. They won 4–0 in {city("2011-11-11")}, {who("Robbie Keane")} scoring twice, and drew 1–1 in Dublin.</p>
  <p>At the finals they lost all three games: 3–1 to {team("Croatia")} in {city("2012-06-10")}, 4–0 to {team("Spain")} in {city("2012-06-14")} and 2–0 to {team("Italy")} in {city("2012-06-18")}. {who("Sean St Ledger")} scored Ireland’s only goal.</p>''',
      qnote="Three points for a win. Group winners and the best runner-up qualified; the other runners-up went into the play-offs.", gnote="Three points for a win. The top two went through.",
      links=[("UEFA_Euro_2012", "Euro 2012, Wikipedia")], credit=[("UEFA_Euro_2012_qualifying_Group_B", "qualifying group"), ("UEFA_Euro_2012_qualifying_play-offs", "play-offs"), ("UEFA_Euro_2012_Group_C", "Group C"), ("UEFA_Euro_2012_squads", "squads")]),
 dict(slug="euro-2016", y=2016, comp="EC", name="Euro 2016", host="France", title="Euro 2016: Ireland in France",
      desc="Long’s goal against Germany, the play-off with Bosnia and Herzegovina, Brady’s winner against Italy and the last 16 against France in Lyon.",
      head="Long beat Germany, Brady beat Italy",
      q="ec2016_q", qpts=3, qname="Qualifying Group D", po="ec2016_po", g="ec2016_g", gpts=3, gname="Group E", ko="ec2016_ko", sq="ec2016_sq", pos=(3, 3), mgr=("martin-oneill", "Martin O'Neill"),
      story=f'''<p>Ireland finished third in Group D behind {team("Germany")} and {team("Poland")}. {who("Shane Long")}’s goal beat Germany, the world champions, 1–0 in Dublin on 8 October 2015. In the play-off they drew 1–1 with {team("Bosnia and Herzegovina")} in {city("2015-11-13")} and won 2–0 in Dublin, {who("Jonathan Walters")} scoring both.</p>
  <p>In France, {who("Wes Hoolahan")} scored in a 1–1 draw with {team("Sweden")}, {team("Belgium")} won 3–0, and {who("Robbie Brady")}’s goal four minutes from time beat {team("Italy")} 1–0 to take Ireland through as one of the best third-placed teams. Brady scored again in the second minute against {team("France")} in {city("2016-06-26")}, but Antoine Griezmann scored twice and France won 2–1.</p>''',
      qnote="Three points for a win. The top two and the best third-placed team qualified; the other third-placed teams went into the play-offs.", gnote="Three points for a win. The top two and the four best third-placed teams went through.",
      links=[("UEFA_Euro_2016", "Euro 2016, Wikipedia")], credit=[("UEFA_Euro_2016_qualifying_Group_D", "qualifying group"), ("UEFA_Euro_2016_qualifying_play-offs", "play-offs"), ("UEFA_Euro_2016_Group_E", "Group E"), ("UEFA_Euro_2016_knockout_stage", "knockout stage"), ("UEFA_Euro_2016_squads", "squads")]),
]
for c in C:
    R = build(c)
    print(c["slug"], "qualifying", len(R["q"]), "play-off", len(R["po"]), "finals", len(R["f"]) + len(R["ko"]), "squad", R["nsq"])
# every campaign is listed in stories.json, so results, reports, search and Ireland in your lifetime link to it
have = {s["slug"] for s in STORIES["campaigns"]}
for c in C: assert c["slug"] in have, ("add to tools/data/stories.json", c["slug"])
