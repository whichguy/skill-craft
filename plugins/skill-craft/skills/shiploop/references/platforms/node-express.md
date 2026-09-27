# Node.js and Express development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when the deployment target or transport changes. Identify who signs in, how, and how authorization is checked before touching state.

`express-session` issues a signed cookie holding only a session ID; the server verifies by looking up that ID in a store. The default `MemoryStore` "will leak memory under most conditions" and "does not scale past a single process" — not for production. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) For federated sign-in, use Passport with `openid-client`'s generic OIDC strategy, configured with the provider's discovery endpoint and client ID/secret. ([passportjs.org/openid-client](https://www.passportjs.org/packages/openid-client/)) Express has no built-in authorization; role checks are hand-written middleware run after session/Passport deserialization (`req.user`). ([expressjs.com/security](https://expressjs.com/en/advanced/best-practice-security/)) Store roles in your own DB table, not the session store, so revocation doesn't require killing every session.

`node:sqlite` is built in but currently Stability 1.2 "Release candidate," not fully stable. ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html)) `better-sqlite3` is synchronous and single-writer; WAL mode lets reads proceed during writes, but SQLite "still serializes writes with exactly one transaction holding the write lock at any moment," and transactions across `ATTACH`ed DBs are not atomic as a set. ([better-sqlite3 performance docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/performance.md)) With PostgreSQL via `pg`, transactions require one dedicated client from `pool.connect()`, not `pool.query()` — mixing clients breaks isolation. Isolation levels are Read Committed (default), Repeatable Read, and Serializable, set via `BEGIN TRANSACTION ISOLATION LEVEL`. ([node-postgres transactions](https://node-postgres.com/features/transactions), [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)) Redis belongs as a session/cache store, not primary transactional storage.

Node is single-threaded per process; running several instances (cluster, PM2, containers) breaks anything held in process memory — in-memory sessions, rate-limit counters, cron schedules, Socket.IO room state — each needs an external store or shared adapter instead. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) `better-sqlite3` writes serialize at the DB level regardless of process count, so multiple instances hitting one file queue on the writer lock. A single-user, client-only tool needs none of this: no session store, no lock, no queue.

Request/response over native `http`/Express is supported by default; polling is client-implemented with no framework support. SSE uses plain `res.write()` over a kept-open `text/event-stream` response, which works with one instance but needs a Redis pub/sub fan-out across several, since a client's stream lives on one process only. `ws` is a low-level standalone WebSocket library; Socket.IO adds rooms, reconnection, and fallback, and across multiple instances requires `@socket.io/redis-adapter`. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/)) Platform push uses `web-push` with VAPID keys from `webpush.generateVAPIDKeys()`. ([web-push GitHub](https://github.com/web-push-libs/web-push))

Redis as an app-level cache needs explicit TTLs; `connect-redis`'s session TTL uses the cookie's expiry or defaults to 86400 seconds. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) Express has no built-in HTTP cache layer — add `Cache-Control` headers or a reverse proxy.

Node's built-in `.env` loading (`node --env-file=.env app.js`, plus `--env-file-if-exists` and `process.loadEnvFile(path)`) is still experimental as of the version checked; environment-set variables win over file values, and the built-in parser does no variable expansion, unlike `dotenv`.

For scheduling, in-process `node-cron` supports overlap prevention and a `noOverlap` distributed-coordination option, but real multi-instance coordination needs that feature or an external scheduler. ([node-cron docs](https://nodecron.com/docs/)) BullMQ (Redis-backed) gives durable queues with retries via `attempts` plus `fixed`/`exponential` backoff; without a backoff function, jobs retry without delay, and there's no built-in dead-letter queue — build one from the `failed` event once attempts are exhausted. At-least-once delivery means handlers must be idempotent: key off job IDs and re-fetch state instead of trusting a re-passed payload. ([BullMQ retrying docs](https://docs.bullmq.io/guide/retrying-failing-jobs))

Check PostgreSQL connection limits, Redis's `maxmemory-policy`, BullMQ concurrency/rate-limit options, and Node's EOL/support window against the linked pages rather than a remembered number.

A local single-process `node app.js` run proves route logic and DB queries, but not multi-instance session sharing, Socket.IO cross-instance delivery, cron dedup under multiple replicas, or real SIGTERM behavior. Test graceful shutdown — the process manager sending SIGTERM and `server.close()` finishing in-flight requests while refusing new ones — by sending a real SIGTERM to a running instance, not Ctrl-C in a dev terminal. ([expressjs.com graceful shutdown](https://expressjs.com/en/advanced/healthcheck-graceful-shutdown/))

## Current facts (as of 2026-09-26)

- Node.js 24 is Active LTS, Node 26 is Current, entering LTS October 2026. ([nodejs.org releases](https://nodejs.org/en/about/previous-releases), [endoflife.date/nodejs](https://endoflife.date/nodejs))
- Express is at ~5.2.x.
- `node:sqlite` is Stability 1.2, "Release candidate." ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- BullMQ documentation is current at [docs.bullmq.io](https://docs.bullmq.io/).
- Socket.IO's Redis adapter is documented for v4. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- `csrf-csrf` is the current maintained package per its npm page. ([npm csrf-csrf](https://www.npmjs.com/package/csrf-csrf))

Recheck these against the linked pages before relying on them.

## Claims to check

- "Express 5 needs no try/catch anywhere." Only promise rejections thrown from an `async` handler passed directly to Express are auto-forwarded; errors thrown inside detached callbacks (timers, event emitters) still need manual handling. ([betterstack Express 5 guide](https://betterstack.com/community/guides/scaling-nodejs/express-5-new-features/))
- "`csurf` is the current standard CSRF package." It is deprecated/archived with no security fixes; use `csrf-sync` or `csrf-csrf`. ([npm csrf-csrf](https://www.npmjs.com/package/csrf-csrf))
- "`node:sqlite` is a fully stable API." It is Stability 1.2, not 2 (Stable). ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- "Default `express-session` `MemoryStore` is fine for small production apps." The docs say it leaks memory and doesn't scale past one process. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- "Socket.IO automatically syncs rooms/broadcasts across horizontally scaled instances." It requires explicitly installing `@socket.io/redis-adapter`. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- "`--env-file` is a drop-in dotenv replacement." It has no variable expansion and is still experimental in the version checked.
