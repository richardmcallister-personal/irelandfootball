#!/usr/bin/env python3
"""Refresh the raw inputs in tools/data/. Run from the repo root, then run build_archive.py.
results/goalscorers/shootouts: martj42/international_results (CC0), Ireland rows only.
wiki_*.txt and wiki_results_<decade>.txt: Wikipedia wikitext (CC BY-SA), read through the site's own /wiki-raw route."""
import csv, io, os, sys, urllib.parse, urllib.request
RAW = "https://raw.githubusercontent.com/martj42/international_results/master/"
WIKI = os.environ.get("WIKI_BASE", "https://irelandfootball.richardmcallister.workers.dev") + "/wiki-raw?title="
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
T = "Republic of Ireland"
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8")
for f in ("results", "goalscorers", "shootouts"):
    src = open(sys.argv[1] + "/" + f + ".csv", encoding="utf-8").read() if len(sys.argv) > 1 else get(RAW + f + ".csv")
    r = csv.DictReader(io.StringIO(src))
    rows = [x for x in r if T in (x["home_team"], x["away_team"])]
    with open(f"tools/data/{f}.csv", "w", newline="", encoding="utf-8") as o:
        w = csv.DictWriter(o, fieldnames=r.fieldnames); w.writeheader(); w.writerows(rows)
    print(f, len(rows))
for name, title in (("matches", "Matches_of_the_Republic_of_Ireland_national_football_team"), ("players", "List_of_Republic_of_Ireland_international_footballers"), ("team", "Republic_of_Ireland_national_football_team")):
    open(f"tools/data/wiki_{name}.txt", "w", encoding="utf-8").write(get(WIKI + urllib.parse.quote(title)))
    print("wiki", name)
# Results by decade (football boxes: goals both ends with minutes, ground, crowd, referee) for the match reports
for name in ("1980–1989", "1990–1999", "2000–2009", "2010–2019", "2020–present"):
    open(f"tools/data/wiki_results_{name[:4]}.txt", "w", encoding="utf-8").write(get(WIKI + urllib.parse.quote("Republic_of_Ireland_national_football_team_results_(" + name + ")")))
    print("wiki results", name)
# Tournament articles for the campaign pages (tools/build_campaigns.py)
CAMPAIGNS = {"wc1990_q": "1990 FIFA World Cup qualification – UEFA Group 6", "wc1990_g": "1990 FIFA World Cup Group F", "wc1990_ko": "1990 FIFA World Cup knockout stage", "wc1990_sq": "1990 FIFA World Cup squads",
             "wc1994_q": "1994 FIFA World Cup qualification – UEFA Group 3", "wc1994_g": "1994 FIFA World Cup Group E", "wc1994_ko": "1994 FIFA World Cup knockout stage", "wc1994_sq": "1994 FIFA World Cup squads",
             "wc2002_q": "2002 FIFA World Cup qualification – UEFA Group 2", "wc2002_po": "2002 FIFA World Cup qualification (UEFA–AFC play-off)", "wc2002_g": "2002 FIFA World Cup Group E", "wc2002_ko": "2002 FIFA World Cup knockout stage", "wc2002_sq": "2002 FIFA World Cup squads",
             "ec2012_q": "UEFA Euro 2012 qualifying Group B", "ec2012_po": "UEFA Euro 2012 qualifying play-offs", "ec2012_g": "UEFA Euro 2012 Group C", "ec2012_sq": "UEFA Euro 2012 squads",
             "ec2016_q": "UEFA Euro 2016 qualifying Group D", "ec2016_po": "UEFA Euro 2016 qualifying play-offs", "ec2016_g": "UEFA Euro 2016 Group E", "ec2016_ko": "UEFA Euro 2016 knockout stage", "ec2016_sq": "UEFA Euro 2016 squads",
             "ire_wc": "Republic of Ireland at the FIFA World Cup", "ire_ec": "Republic of Ireland at the UEFA European Championship"}
os.makedirs("tools/data/campaigns", exist_ok=True)
for f, title in CAMPAIGNS.items():
    open(f"tools/data/campaigns/{f}.txt", "w", encoding="utf-8").write(get(WIKI + urllib.parse.quote(title.replace(" ", "_"))))
print("wiki campaigns", len(CAMPAIGNS))
