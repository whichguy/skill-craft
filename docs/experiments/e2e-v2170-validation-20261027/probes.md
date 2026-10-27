# Probes of the shipped Sonnet product (v2170-sonnet-battleship-491d9a, HEAD 41a9f39; server.js and game.js equal 388263d)

Run on a `git archive` copy, never the run's worktree.
- `curl --path-as-is http://127.0.0.1:39518//` -> 000; server.log: `TypeError: Invalid URL` (input '//') at `new URL(req.url, 'http://localhost')`; the process exits, and every later request gets 000.
- `createServer({maxGames: 0})`: accepted; the first fire on a new game -> `404 {"error":"unknown game"}` (evicted at creation).
- `createServer({maxGames: -1})`: `while (games.size > maxGames)` never ends; the probe was still spinning after 8 s and was killed (an earlier probe sat at 97% CPU).
- Page `onFire`: no check that a reply belongs to the current `gameId`; a stale reply's `gameOver` disables the new board (by reading).
Baseline 01b9b3 fixed each one in a per-step implement review: 2d7c7e7 (GET // -> 400), b46f76b (stale reply ignored), createStore option validation.

# DeepSeek W2 before its item review (v2170-ds-battleship-759a03, ce5341c)
- `curl --path-as-is http://127.0.0.1:39519//` -> 000; server.log `TypeError: Invalid URL`; `server.js:146` parses `new URL(request.url, …)` outside any try.
- `createServer({random})` validates its only option (TypeError when not a function): no store-options defect here.
- After the W2 item review (77095e7): `GET //` -> `400 {"error":"the request target is not a URL path"}`, then `GET /` -> 200. Review passes: 1 non-trivial (3 defects: listen on every interface while claiming localhost, ...), 2 non-trivial (the URL-parse crash), 3 trivial.
- DeepSeek page (public/index.html, written in W2, at 2183e09): `inFlight` locks New game while a shot is in flight (`:60` comment, `:119 if (inFlight) return;`), so a stale reply cannot land on a new game: the bug is absent by design.
