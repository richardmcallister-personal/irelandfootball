# Ireland Football: where things stand (2 Nov 2026)

Read CLAUDE.md first.

## Done

Pages: hub, season, squad, results, players, player, opponents, opponent, records, managers, kits, search, match centre. Real crests, logos, kits and iPhone launch images are in.
Archive: 639 matches 1924 to 4 Oct 2026, 566 players, 87 opponents, 30 manager spells. Tested locally with mocked standings and squad, and real fixtures and match data read through manutd.wiki.

## Live

Deployed from `main` by Workers Builds to irelandfootball.richardmcallister.workers.dev. Fixtures, group table, squad, match centre, Wikipedia and portraits all checked against real data.

## Known gaps

- Scorers: 442 of 870 goals. None for friendlies; 6 of 23 Nations League goals missing.
- Feed history for team 776 (`/api/team-season?season=Y`): see the year-by-year result below. Next data job: fill recent friendly scorers and line-ups from it.
- Totals differ slightly from eu-football (639 games, 246 W against 247, 181 D against 180, 870 GF against 867, 775 GA against 772). See tools/data/reconcile.txt. Which early and unofficial games count is still Richard's call.
- The results archive only updates when the builders are re-run. There is no scheduled refresh yet.

## Next, in order

1. Richard: buy the domain, then add the routes in wrangler.jsonc.
2. Fill recent scorers and line-ups from the feed.
3. Club form: how each squad player is doing at his club. Needed before launch, as Ireland only play about 10 games a year.
4. Port from manutd.wiki: goal alerts, Ask, trips, calendar, where to watch, timeline, compare, Analytics with consent.
5. Weekly data refresh as a scheduled task.
6. Ask eu-football.info about older line-ups and friendly scorers.
