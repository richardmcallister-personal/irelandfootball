# Ireland Football: where things stand (7 Nov 2026)

Read CLAUDE.md first.

## Done

Pages: hub, season, squad, results, players, player, opponents, opponent, records, managers, manager, kits, search, match centre. Real crests, logos, kits and iPhone launch images are in.
Archive: 639 matches 1924 to 4 Oct 2026, 566 players, 87 opponents, 30 manager spells. Tested locally with mocked standings and squad, and real fixtures and match data read through manutd.wiki.

## Live

Deployed from `main` by Workers Builds to irelandfootball.wiki (also irelandfootball.richardmcallister.workers.dev). Fixtures, group table, squad, match centre, Wikipedia and portraits all checked against real data.

## Alerts

Web Push on the hub, minute cron in the Worker. The live logic was replayed offline against the Ireland v Austria feed data, including a ruled-out goal. First live run: Austria v Ireland, 14 Nov 2026.

## Calendar and where to watch

`/calendar.ics` (all games, or `?m=<fixture id>` for one) is built from the fixtures feed, one event per fixture id, so a subscribed calendar follows a moved kick-off. Where to watch is on the hub and match pages, Nations League only.

## Great days and campaigns

Static pages from `tools/build_stories.py`: `/matches/ireland-romania-1990/`, `/campaigns/euro-1988/`. Next candidates: other tournament campaigns and big games.

## Kit library

The Kits page has a new section of 215 shirts (420 photos) from the James Nolan Memorial Collection, added alongside the existing kits. Design and own, wishlist, notes and Buy links come from manutd.wiki's shirts page, with the store at `/collection` (hashed key, this site's KV). Buy links search for the year and type, not the exact shirt. Shirts from 2021 on are listed in `tools/data/kits_extra.csv`, most awaiting photos from Richard. No permission from Eddie O'Mahony yet; Richard has a draft request. Not used for training or leisure tops, prototypes or the LA Galaxy shirts.

## Editorial front page: trial on dev.irelandfootball.wiki (branch `redesign`)

Branch `redesign` builds the Worker `irelandfootball-dev` (`wrangler.jsonc` env.dev, deploy command `npx wrangler deploy --env dev`), served at dev.irelandfootball.wiki. Every data call is proxied to irelandfootball.wiki (`UPSTREAM`), so the dev Worker has no API key, KV or crons and sends no alerts; its pages carry `x-robots-tag: noindex`. Not merged to main.

What the trial changes: an "Editorial skin" block at the end of `mu.css` (cream paper, deep green, Source Serif 4 headlines, small-caps labels, one orange accent; Anton stays for scores), the serif font added to every page's font link, and a new front page: next-match strip, a lead story (kicker, headline, deck, shirt and crest of the era; rotates daily, or the anniversary story within a week of its date), Start here, three doors (current team, a century of Ireland, every result), a record strip, then the existing panels under "This season". From three hours before kick-off to eight hours after, the match card takes the lead slot. New `/campaigns/` index page, written by `build_campaigns.py`. No photography: the mock-up's player photos are not used.

## Pick your XI

`/xi/`: the manutd.wiki "Pick your XI" builder (tap a position, pick from a dialog with natural positions first) in Ireland's colours, with three sources: everyone capped since 1924, one tournament squad (Euro ’88 to Euro 2016, from `site/history/squads.json`, written by `build_stories.py` and `build_campaigns.py`), or the latest squad (live feed, with portraits). Seven formations, an optional title and name. The share card is a 1080×1350 PNG drawn on a canvas from the theme tokens (green, Anton, Inter, crest): "Share image" uses the phone's share sheet with the file, otherwise it downloads. The page URL holds the XI (`?s=&f=&p=slugs&t=&n=`), so a link reopens it, and the Worker turns it into a link preview with the title and the eleven names. The last XI is kept in the browser. Linked from Explore on the hub and from the Squad page.

## Milestone watch and milestone alerts

`/milestones/`: the latest squad plus anyone capped in the last 18 months. Shows who is within five games of 10, 25, 50 or 100 caps, within three goals of 5, 10, 20, 30, 40 or 50 goals, where each stands on the all-time caps and scorers lists with the next former player to draw level with and pass, and milestones reached in the last 12 months (only where the archive has every appearance or goal for that player). Counts come from `players.json`, so they move when the archive is rebuilt after each window. Linked from Explore on the hub; the next fixture is shown as "Next chance".

Push alerts: a new "Milestones" option (on by default) sends one alert per player at full-time: a 10th, 25th, 50th or 100th cap, a 5th, 10th, 20th … 50th goal, or a new place in the all-time top ten for caps or goals. The Worker reads `players.json` and `matches.json` from the site; if the archive doesn't have the game yet it adds one cap, and the goals from the feed. Feed names are matched to the archive as the squad page does (surname, plus the initial when the feed gives one); a player it can't match is skipped. Existing subscribers get it too unless they turn it off.

## Campaign pages for every major finals

`/campaigns/<slug>/` for Euro ’88 (written by hand in `build_stories.py`), Italia ’90, USA ’94, World Cup 2002, Euro 2012 and Euro 2016 (`world-cup-1990`, `world-cup-1994`, `world-cup-2002`, `euro-2012`, `euro-2016`, built by `tools/build_campaigns.py`). Each has a short story, the qualifying table, every Ireland qualifying and play-off game with scorers, the finals games and group table, the shirts and the squad with caps at the time. Tables, scores, scorers and squads come from Wikipedia's tournament articles (`tools/data/campaigns/`); the script fails if an Ireland game disagrees with the archive or a table disagrees with its games. The story paragraphs are written in the script and in `ga.json` blocks; facts in them were checked against those articles and the archive. Listed in `tools/data/stories.json`, so Results, match reports, search and Ireland in your lifetime link to them.

## Ireland in your lifetime

`/lifetime/?y=1975` (add `&vs=2001` to compare two people). Enter a birth year and get: played, won, drawn, lost since then, the first game of that year (or the next one if Ireland didn't play), biggest win and heaviest defeat since, major finals, the opponents faced most often, top scorers (with how many goals have a named scorer) and the managers. Years before 1924 start at the first game. Built in the browser from the archive. The Worker rewrites the page title and preview tags for `?y=`, so a shared link shows that person's numbers in WhatsApp or iMessage. Linked from Explore on the hub and from Records.

The latest manutd.wiki design changes (bordered cards, uppercase section labels, next match leading the hub) were started on 7 Nov and stopped; they sit in `git stash` ("latest manutd design port"), not live.

## Match reports

`/report/?d=YYYY-MM-DD` for every game from 1986 (416), linked from the score and a "Match report" note on Results, from Opponent pages and from On this day on the hub. Built in the browser from the archive plus `reports.json`: score card with ground, crowd and referee, goals at both ends in order with the running score, shoot-outs kick by kick, debuts, final caps, scorers' Ireland totals, manager, the line-up where the feed has one (2012 on), the record against that opponent with previous and next meetings, and previous and next game. 406 games have a Wikipedia box; 399 have goals that agree with the archive. The rest show the archive's own scorers; see `tools/data/reconcile_reports.txt`. Fixed on the way: Wikipedia's short month names ("2 Jun 2013") were not read, so some debut dates came from the feed instead (Stephen Quinn's was wrong).

## Design

Moved to manutd.wiki's November 2026 design: `site/mu.css` is its stylesheet with Ireland's green and a red for defeats (`--loss`), then Ireland's own rules after the "Ireland additions" marker. Green masthead that stays at the top, Anton for the name, scores and kick-off times, Inter for text, sentence case, white cards on grey, the phone tab bar. One "Add to calendar" menu (`MU.calMenu`) on the hub, match centre and season pages. The hub follows manutd.wiki's: match card with both crests, form and table tiles, Coming up, latest result report with the last five, on this day, the group table and an Explore list (Great days now live there). To take a later manutd.wiki CSS fix, copy its rule across and keep the tokens.

## Irish version

Language picker in the header of every page; the choice is saved in the browser, and `?lang=ga` links straight to Irish. See CLAUDE.md. Match alerts and calendar feeds are still English.

## Known gaps

- Scorers: friendlies before about 2017 are mostly unnamed; Keane and all listed hat-tricks are now in, without minutes. Line-ups start about 2017.
- Feed history for team 776 (`/api/team-season?season=Y`): see the year-by-year result below. Next data job: fill recent friendly scorers and line-ups from it.
- Totals differ slightly from eu-football (639 games, 246 W against 247, 181 D against 180, 870 GF against 867, 775 GA against 772). See tools/data/reconcile.txt. Which early and unofficial games count is still Richard's call.
- Results update through the weekly scheduled task, so a game can take up to a week to reach the archive.

## Next, in order

1. Port from manutd.wiki: timeline, compare, trips, Ask. Analytics with consent.
2. Ask eu-football.info about older line-ups and friendly scorers.
