#!/usr/bin/env python3
"""Refresh the raw inputs in tools/data/. Run from the repo root, then run build_archive.py.
results/goalscorers/shootouts: martj42/international_results (CC0), Ireland rows only.
wiki_*.txt: Wikipedia wikitext (CC BY-SA), read through the site's own /wiki-raw route."""
import csv, io, os, sys, urllib.parse, urllib.request
RAW = "https://raw.githubusercontent.com/martj42/international_results/master/"
WIKI = os.environ.get("WIKI_BASE", "https://irelandfootball.wiki") + "/wiki-raw?title="
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
