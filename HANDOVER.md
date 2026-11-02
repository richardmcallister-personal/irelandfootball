# Ireland Football: where things stand (2 Nov 2026)

Read CLAUDE.md first.

## Done

Pages: hub, season, squad, results, players, player, opponents, opponent, records, managers, kits, search, match centre. Real crests, logos, kits and iPhone launch images are in.
Archive: 639 matches 1924 to 4 Oct 2026, 566 players, 87 opponents, 30 manager spells. Tested locally with mocked standings and squad, and real fixtures and match data read through manutd.wiki.

## Not tested until the Worker has its own key

`/api/fixtures`, `/api/standings` and `/api/squad` for team 776 have not run on this Worker. The mocks in local testing assumed the feed's normal shape.

## Known gaps

- Scorers: 442 of 870 goals. None for friendlies; 6 of 23 Nations League goals missing.
- The feed's history depth for team 776 is untested. Once the key is on, use it to fill recent scorers and line-ups.
- Totals differ slightly from eu-football (639 games, 246 W against 247, 181 D against 180, 870 GF against 867, 775 GA against 772). See tools/data/reconcile.txt. Which early and unofficial games count is still Richard's call.
- The results archive only updates when the builders are re-run. There is no scheduled refresh yet.

## Next, in order

1. Richard: connect the repo to a new Worker, add API_FOOTBALL_KEY, buy the domain.
2. Check live routes.
3. Club form: how each squad player is doing at his club. Needed before launch, as Ireland only play about 10 games a year.
4. Port from manutd.wiki: goal alerts, Ask, trips, calendar, where to watch, timeline, compare, Analytics with consent.
5. Weekly data refresh as a scheduled task.
6. Ask eu-football.info about older line-ups and friendly scorers.
