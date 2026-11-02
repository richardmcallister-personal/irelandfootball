# Ireland Football: where things stand (2 Nov 2026)

Read CLAUDE.md first.

## Done

Pages: hub, season, squad, results, players, player, opponents, opponent, records, managers, manager, kits, search, match centre. Real crests, logos, kits and iPhone launch images are in.
Archive: 639 matches 1924 to 4 Oct 2026, 566 players, 87 opponents, 30 manager spells. Tested locally with mocked standings and squad, and real fixtures and match data read through manutd.wiki.

## Live

Deployed from `main` by Workers Builds to irelandfootball.wiki (also irelandfootball.richardmcallister.workers.dev). Fixtures, group table, squad, match centre, Wikipedia and portraits all checked against real data.

## Known gaps

- Scorers: friendlies before about 2017 have none. Line-ups start about 2017.
- Feed history for team 776 (`/api/team-season?season=Y`): see the year-by-year result below. Next data job: fill recent friendly scorers and line-ups from it.
- Totals differ slightly from eu-football (639 games, 246 W against 247, 181 D against 180, 870 GF against 867, 775 GA against 772). See tools/data/reconcile.txt. Which early and unofficial games count is still Richard's call.
- Results update through the weekly scheduled task, so a game can take up to a week to reach the archive.

## Next, in order

1. Port from manutd.wiki: goal alerts, Ask, trips, calendar, where to watch, timeline, compare. Analytics with consent.
2. Ask eu-football.info about older line-ups and friendly scorers.
