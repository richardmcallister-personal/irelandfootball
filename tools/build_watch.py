#!/usr/bin/env python3
"""Turn UEFA's Nations League broadcaster list (tools/data/uefa_nl_broadcasters.txt) into site/watch.json.
Each country lists only who can show an Ireland game: "England matches only" and the like are dropped.
Run from the repo root: python3 tools/build_watch.py. Needs pycountry."""
import json, re, pycountry
CHECKED = "2026-11-02"
URL = "https://www.uefa.com/uefanationsleague/news/02a9-219ae5c877f5-740390ccb3e5-1000--where-to-watch-the-nations-league-tv-broadcast-partners-li/"
CODES = {"Republic of Ireland": "IE", "Russia": "RU", "Türkiye": "TR", "Kosovo": "XK", "Vatican City": "VA", "United Kingdom": "GB", "United States of America": "US", "China PR": "CN", "South Korea": "KR", "North Korea": "KP", "Hong Kong SAR": "HK", "Macau SAR": "MO", "Taiwan/Chinese Taipei": "TW", "Iran": "IR", "Syria": "SY", "Laos": "LA", "Vietnam": "VN", "Moldova": "MD", "Bolivia": "BO", "Venezuela": "VE", "Czechia": "CZ", "Tanzania": "TZ", "Palestine (Gaza strip & West Bank)": "PS", "Ivory Coast": "CI", "Democratic Republic of Congo": "CD", "Congo Republic": "CG", "Cape Verde": "CV", "British Virgin Islands": "VG", "U.S. Virgin Islands": "VI", "Micronesia": "FM", "French Guyana": "GF", "Falkland Islands": "FK", "Bonaire": "BQ", "Curaçao": "CW", "Réunion": "RE", "São Tomé and Príncipe": "ST", "St. Kitts and Nevis": "KN", "St. Lucia": "LC", "St. Vincent & the Grenadines": "VC", "Antigua & Barbuda": "AG", "Trinidad & Tobago": "TT", "Turks & Caicos Islands": "TC", "Wallis & Futuna": "WF", "St. Barts": "BL", "St. Martin": "MF", "St. Pierre & Miquelon": "PM", "St. Helena and Ascension": "SH", "Mariana Islands": "MP", "French Southern and Antarctic Lands": "TF"}
SKIP = {"Midway", "Saba", "St. Christopher", "St. Eustatius", "Swaziland", "Tibet", "Tortola"}   # no ISO code of their own, or a second name for a listed country
NAME = {"United States of America": "United States", "Republic of Ireland": "Ireland"}
countries = {}; missed = []
for name, rest in re.findall(r"\*\*([^*]+)\*\*\s*:\s*(.*?)(?=\s*\*\*|\Z)", open("tools/data/uefa_nl_broadcasters.txt", encoding="utf-8").read(), re.S):
    name = name.strip()
    if name in SKIP: continue
    code = CODES.get(name)
    if not code:
        try: code = pycountry.countries.lookup(name).alpha_2
        except LookupError: missed.append(name); continue
    who = []
    for b in re.split(r",\s*", rest.strip()):
        b = b.strip()
        if not b or re.search(r"\b(only)\)", b): continue
        who.append(re.sub(r"\s*\(.*\)$", "", b).strip())
    countries[code] = {"n": NAME.get(name, name), "nl": who}
countries["GB"] = {"n": "United Kingdom", "nl": ["Prime Video"], "nlNote": "Prime Video has the games not involving the UK's own teams. ESPN reported the Ireland v Austria game in October as pay per view."}
assert not missed, missed
assert countries["IE"]["nl"] == ["RTÉ", "Virgin Media Ireland"] and countries["SE"]["nl"] == ["Viaplay"] and countries["US"]["nl"] == ["FOX Sports", "FuboTV", "ViX"]
json.dump({"checked": CHECKED, "sources": {"nl": {"t": "UEFA: where to watch the 2026/27 Nations League", "u": URL}}, "countries": countries}, open("site/watch.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
print(len(countries), "countries")
