# Ireland Football: where things stand (2 Nov 2026)

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

## Known gaps

- Scorers: friendlies before about 2017 are mostly unnamed; Keane and all listed hat-tricks are now in, without minutes. Line-ups start about 2017.
- Feed history for team 776 (`/api/team-season?season=Y`): see the year-by-year result below. Next data job: fill recent friendly scorers and line-ups from it.
- Totals differ slightly from eu-football (639 games, 246 W against 247, 181 D against 180, 870 GF against 867, 775 GA against 772). See tools/data/reconcile.txt. Which early and unofficial games count is still Richard's call.
- Results update through the weekly scheduled task, so a game can take up to a week to reach the archive.

## Next, in order

1. Port from manutd.wiki: timeline, compare, trips, Ask. Analytics with consent.
2. Ask eu-football.info about older line-ups and friendly scorers.
