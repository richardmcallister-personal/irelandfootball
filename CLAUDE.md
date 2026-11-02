# Ireland Football: working notes for Claude

Richard's site for the Republic of Ireland men's senior team. Forked from manutd.wiki (repo SITE1), which it must not affect.
Plain static pages + one Cloudflare Worker. No build step, no framework.

## Layout

```
site/            everything served: one index.html per page, shared mu.css + mu.js
site/history/    archive JSON, all written by tools/build_archive.py (never edit by hand)
site/assets/     crest and icon sizes (tools/make_icons.py), crests/, comps/, orgs/, kits/, crests-old/, splash/, flags/ (flag-icons, MIT)
worker.js        API-Football proxy + KV cache, Wikipedia proxy, portraits
wrangler.jsonc   Worker config; KV namespace irelandfootball-mu-cache, separate from manutd.wiki
tools/data/      raw inputs and reconcile.txt (every disagreement between sources)
```

## Data sources

| Data | Source | Licence |
|---|---|---|
| Results, competitive scorers | martj42/international_results, `tools/data/*.csv` | CC0 |
| Two 1924 games the dataset lacks | `tools/data/extra_matches.csv` (Wikipedia + eu-football agree) | |
| Venue, manager, match notes, caps list, manager table | Wikipedia wikitext | CC BY-SA, credited in the footer |
| Live fixtures, tables, squad, match centre | API-Football, team 776, through the Worker | paid plan |

11v11.com and eu-football.info are not sources: 11v11's terms bar publishing its data, and eu-football has not given permission. Don't scrape them.

Manager of each game (`ms` on match rows): from Wikipedia's match list from 1969; before that a spell's games are placed only where one unbroken run in its years matches Wikipedia's figures exactly. Anything else goes in reconcile.txt. Article titles are in `tools/data/manager_wiki.json`; check them, as the Wikipedia route falls back to search and can land on the wrong person.

## Conventions

- Refresh data: `python3 tools/fetch_sources.py` (needs a deployed site for Wikipedia, or set WIKI_BASE), then `python3 tools/build_archive.py`, review `git diff tools/data/reconcile.txt`, commit.
- National teams have no club season. The Worker asks for this year's and last year's feed labels and joins them.
- Opponents use association crests (`site/assets/crests/`, Richard's files, listed in `HAS` in mu.js). Former countries (Czechoslovakia, Soviet Union, Yugoslavia, West Germany) use one general federation mark, not an era-accurate shirt badge; see `tools/data/asset_sources.csv`. Never use the Ulster Banner on this site.
- Competition logos: `MU.comp` for feed names, `MU.compRow` for archive rows (the edition the game belonged to). Originals are in `~/Documents/Projects/ireland-assets/` on Richard's Mac; `site/assets` holds resized copies.
- Token names (`--red` etc.), `mu.js` and `mu.css` keep their manutd.wiki names so fixes port across. `--red` is green here. Never hard-code a colour in a page.
- Before pushing: `npx -y esbuild@0.24.0 worker.js --format=esm --log-level=error --outfile=/tmp/x.js`, `npx -y wrangler@latest deploy --dry-run --outdir /tmp/wr`, `node --check site/mu.js`, and `node --check` each page's last script block.
- After deploying: check light and dark at 1280 and 390 wide, with no `pageerror`, overflow, 4xx or 5xx. Use a browser user agent; don't use one to get past a third party's bot check.
- Commit as Richard (`-c user.name="Richard McAllister" -c user.email=richardmcallister@gmail.com`), with a one-line summary of what changed for the site.
- Secrets exist only as Worker secrets. Never in the repo or chat.
- Richard's preferences: concise, plain words; `.` decimal point and no thousands separators; checks on iPhone and Mac Chrome.
