# Fact Sheet: Self-Hosted Node.js + Express (single VM/container)

## 1. Identity and sign-in for end users
- Node 24 is Active LTS, Node 22 is Maintenance LTS, Node 26 is Current (entering LTS Oct 2026) — pick 24 or 26 for new self-hosted apps. ([nodejs.org/releases](https://nodejs.org/en/about/previous-releases), [endoflife.date](https://endoflife.date/nodejs))
- Sessions: `express-session` issues a signed cookie holding only a session ID; the server verifies by looking up that ID in a store. Default `MemoryStore` "will leak memory under most conditions" and "does not scale past a single process" — not for production. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- For federated sign-in, use Passport with `openid-client`'s generic OIDC strategy (recommended over the older `passport-openidconnect`), configured with the provider's discovery endpoint, client ID/secret. ([passportjs.org/openid-client](https://www.passportjs.org/packages/openid-client/))

## 2. Authorization patterns
- Express itself has no built-in authorization; role/permission checks are hand-written middleware run after session/Passport deserialization (`req.user`). ([expressjs.com/security](https://expressjs.com/en/advanced/best-practice-security/))
- Store roles in your own DB table, not in the session store, so revocation doesn't require killing every session.

## 3. State and storage
- `node:sqlite` is built in but currently **Stability 1.2 "Release candidate"**, not fully stable, per the live docs page. ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- `better-sqlite3` is synchronous, single-writer; WAL mode lets reads proceed during writes but "SQLite still serializes writes with exactly one transaction holding the write lock at any moment." Transactions across `ATTACH`ed DBs are not atomic as a set. ([WiseLibs/better-sqlite3 performance docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/performance.md))
- PostgreSQL via `pg`: transactions require one dedicated client (`pool.connect()`), not `pool.query()` — mixing clients breaks isolation. Isolation levels: Read Committed (default), Repeatable Read, Serializable, set via `BEGIN TRANSACTION ISOLATION LEVEL ...`. ([node-postgres transactions](https://node-postgres.com/features/transactions), [PostgreSQL 13.2 Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html))
- Redis: use as session/cache store, not primary transactional storage.

## 4. Concurrency control
- Node is single-threaded per process/event loop; running several instances (cluster, PM2, containers) breaks anything held in process memory: in-memory sessions, in-memory rate-limit counters, in-memory cron schedules, in-memory Socket.IO room state. Fix each with an external store (Redis) or a shared adapter. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- `better-sqlite3` writes serialize at the DB level regardless of process count — multiple instances hitting one SQLite file will queue on the writer lock. ([better-sqlite3 performance docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/performance.md))

## 5. Connectivity channels
- Request/response: native `http`/Express — supported by default.
- Polling: implement client-side; no built-in framework support.
- SSE: plain `res.write()` over a kept-open `text/event-stream` response; works with one instance, but multiple instances need a fan-out (Redis pub/sub) since a client's stream lives on one process only.
- WebSockets: `ws` is a low-level standalone WebSocket server library; `Socket.IO` adds rooms/reconnection/fallback and, for multiple instances, requires the `@socket.io/redis-adapter` — "when scaling to multiple Socket.IO servers, you need to replace the default in-memory adapter." ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- Platform push: `web-push` (npm) implements the Web Push protocol with VAPID keys generated via `webpush.generateVAPIDKeys()`. ([web-push GitHub](https://github.com/web-push-libs/web-push))

## 6. Caching options and staleness
- Redis as app-level cache: set explicit TTLs; e.g., `connect-redis` session TTL "will use \[the cookie's expires date] as the TTL, otherwise it will expire sessions using the ttl option (default: 86400 seconds or one day)." ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- No built-in HTTP cache layer in Express; add `Cache-Control` headers manually or a reverse proxy.

## 7. Secrets custody
- Node has built-in `.env` loading: `node --env-file=.env app.js` (still marked experimental as of the version checked), plus `--env-file-if-exists` and a programmatic `process.loadEnvFile(path)`. Environment-set variables take precedence over file values, and **the built-in parser does not do variable expansion** (unlike `dotenv`). ([nodejs.org env docs via search](https://nodejs.org/learn/command-line/how-to-read-environment-variables-from-nodejs))

## 8. Scheduling, queues, background work
- In-process cron: `node-cron` supports "overlap prevention, distributed coordination" via a `noOverlap` option, but true multi-instance coordination needs its distributed-lock feature or an external scheduler. ([node-cron docs](https://nodecron.com/docs/))
- Durable queues: BullMQ (Redis-backed). Retries via `attempts` + backoff (`fixed`/`exponential`); "if you do not specify a back-off function, jobs will be retried without delay." No built-in dead-letter queue — build one from the `failed` event once attempts are exhausted. At-least-once delivery means job handlers must be idempotent (key off IDs, re-fetch state, don't trust re-passed payload). ([BullMQ retrying docs](https://docs.bullmq.io/guide/retrying-failing-jobs))

## 9. Limits to check
- PostgreSQL connection limits: [postgresql.org runtime config connections](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- Redis memory/eviction limits: consult Redis docs for `maxmemory-policy`.
- BullMQ concurrency/rate-limit options: [docs.bullmq.io](https://docs.bullmq.io/)
- Node.js EOL/support windows: [endoflife.date/nodejs](https://endoflife.date/nodejs)

## 10. Deployment and verification surface
- A local single-process `node app.js` run proves route logic and DB queries, but **does not** prove: multi-instance session sharing, Socket.IO cross-instance delivery, cron dedup under multiple replicas, or real SIGTERM behavior under a process manager — those require an actual multi-process/container test.
- Graceful shutdown: "when you deploy a new version... the process manager will send a SIGTERM," and `server.close()` "instructs the Node.js HTTP server to not accept any more requests and finish all running requests." Test this by sending real SIGTERM to a running instance, not just Ctrl-C in a dev terminal. ([expressjs.com healthcheck-graceful-shutdown](https://expressjs.com/en/advanced/healthcheck-graceful-shutdown/))

## 11. Common false claims and corrections
- **False:** "Express 5 needs no try/catch anywhere." **Correction:** only promise rejections thrown from an `async` handler passed directly to Express are auto-forwarded; errors thrown inside detached callbacks (timers, event emitters) still need manual handling. ([betterstack Express 5 guide](https://betterstack.com/community/guides/scaling-nodejs/express-5-new-features/))
- **False:** "`csurf` is the current standard CSRF package." **Correction:** csurf is deprecated/archived with no security fixes; use `csrf-sync` (session-based) or `csrf-csrf` (double-submit cookie). ([npm csrf-csrf](https://www.npmjs.com/package/csrf-csrf))
- **False:** "`node:sqlite` is a fully stable API." **Correction:** it's Stability 1.2 "Release candidate," not 2 (Stable), on the current docs. ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- **False:** "Default express-session MemoryStore is fine for small production apps." **Correction:** the docs explicitly say it leaks memory and doesn't scale past one process. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- **False:** "Socket.IO automatically syncs rooms/broadcasts across horizontally scaled instances." **Correction:** requires explicitly installing `@socket.io/redis-adapter`. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- **False:** "`--env-file` is a drop-in dotenv replacement." **Correction:** it doesn't support variable expansion and is still experimental in the version checked.

**As of:** Node.js 24 (Active LTS)/26 (Current, LTS Oct 2026); Express ~5.2.x; `node:sqlite` per nodejs.org/api/sqlite.html (Stability 1.2); BullMQ per docs.bullmq.io; Socket.IO v4 Redis adapter docs; express-session/connect-redis READMEs; csrf-csrf npm page — all checked 2026-09-26.
