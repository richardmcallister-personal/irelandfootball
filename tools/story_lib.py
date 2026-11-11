"""Shared helpers for the story and campaign pages: page chrome from site/kits/index.html, links, tables."""
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
    head = head.replace('<meta name="robots" content="noindex,noimageindex">', "")
    head = re.sub(r"<style>.*?</style>", "<style></style>", head, flags=re.S)
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

