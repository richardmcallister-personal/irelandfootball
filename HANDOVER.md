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
