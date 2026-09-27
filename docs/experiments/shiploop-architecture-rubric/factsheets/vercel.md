# Vercel + Next.js Platform Fact Sheet

## 1. Identity and sign-in
- Next.js ships no built-in auth; identity comes from a library (Auth.js/NextAuth v5, Clerk, Better Auth) or hosted IdP. [Next.js Auth guide](https://nextjs.org/docs/app/guides/authentication)
- Auth.js JWT strategy: signed/encrypted HttpOnly cookie, verified server-side by decrypting with the server secret — no DB call. Database strategy: cookie holds only a session ID, verified via DB lookup each request. [Auth.js session strategies](https://authjs.dev/concepts/session-strategies)
- Clerk: server verifies via `auth()` from `@clerk/nextjs/server` in Server Components/Actions/Route Handlers. [Clerk `auth()` reference](https://clerk.com/docs/reference/nextjs/app-router/auth)

## 2. Authorization patterns
- Next.js's own guidance: Middleware is only for "optimistic" redirects; real authorization must live in a Data Access Layer next to the data fetch. [Next.js Data Security guide](https://nextjs.org/docs/app/guides/data-security)
- CVE-2025-29927 let attackers spoof `x-middleware-subrequest` to skip Middleware entirely, bypassing any auth logic placed only there; fixed in 14.2.25/15.2.3+. [GHSA-f82v-jwr5-mffw](https://github.com/advisories/GHSA-f82v-jwr5-mffw)
- Server Actions are POST-only with Origin/Host checks and encrypted action IDs, but Next.js still requires an authorization check inside every action body. [Security in Server Components/Actions](https://nextjs.org/blog/security-nextjs-server-components-actions)

## 3. State/storage, consistency, transactions
- Vercel-native: Blob (`@vercel/blob`, immutable content-addressed files) and Edge Config (`@vercel/edge-config`, read-optimized key/value). [Vercel Storage overview](https://vercel.com/docs/storage)
- Everything else (Postgres, Redis, Mongo) comes via Marketplace integrations (Neon, Supabase, Upstash, etc.); Vercel Postgres/KV were retired and migrated to Neon/Upstash in Dec 2024. [Marketplace Storage](https://vercel.com/docs/marketplace-storage)
- Consistency/transaction guarantees are set entirely by the chosen provider — Vercel imposes none. Unverified: per-provider SLAs (check provider docs).

## 4. Concurrency control
- Functions auto-scale to 30,000 (Hobby/Pro) or 100,000+ (Enterprise) concurrent instances with no shared locking primitive. [Functions limits](https://vercel.com/docs/functions/limitations)
- Locking (row versions, `SELECT … FOR UPDATE`, Redis `WATCH`) must be implemented in the Marketplace database itself — unverified in Vercel docs, standard DB practice.
- Vercel Queues delivers at-least-once, so concurrent duplicate processing is expected and must be deduped by the consumer. [Queues concepts](https://vercel.com/docs/queues/concepts)

## 5. Connectivity channels
- Request/response: standard Route Handlers/Server Actions, Node or Edge runtime. [Runtimes](https://vercel.com/docs/functions/runtimes)
- Streaming/SSE: supported; Edge must start a response within 25s, can stream to 300s; Node/Bun/Python stream up to `maxDuration`. [Functions limits](https://vercel.com/docs/functions/limitations)
- WebSockets: natively supported (Public Beta, June 2026) on Fluid compute; a connection pins to one instance for its life, closes at `maxDuration`, new connections aren't guaranteed the same instance — cross-instance state needs an external store. Next.js lacks a native upgrade API; use `experimental_upgradeWebSocket()` from `@vercel/functions`. [WebSockets docs](https://vercel.com/docs/functions/websockets)
- Platform push (FCM/APNs) is not a Vercel primitive — unverified, call it from a Function/Workflow yourself.

## 6. Caching and staleness
- Next.js 16's `"use cache"` + `cacheLife()`/`cacheTag()` (Cache Components) replace implicit fetch caching, with explicit `stale`/`revalidate`/`expire` windows. [`use cache` directive](https://nextjs.org/docs/app/api-reference/directives/use-cache)
- Data Cache is regional, per-environment, persists across deployments; busted via `revalidateTag`/`revalidatePath`/`updateTag`. [Data Cache](https://vercel.com/docs/caching/runtime-cache/data-cache)
- CDN cache respects `s-maxage`/`stale-while-revalidate` (max 1 year, best-effort — rarely-hit paths can evict early); `proxy-revalidate`/`stale-if-error` unsupported; `Set-Cookie`, `Authorization`, or high-cardinality `Vary` (e.g. `Cookie`) responses are never cached. [CDN Cache](https://vercel.com/docs/caching/cdn-cache)

## 7. Secrets custody
- "Sensitive" env vars: encrypted at rest per-project key, plaintext never shown again after creation. "Regular" vars: stored/displayed as plaintext to anyone with project access. [Sensitive env vars](https://vercel.com/docs/environment-variables/sensitive-environment-variables)
- Marketplace DB/Redis credentials are injected as env vars under this same model. [Marketplace Storage](https://vercel.com/docs/marketplace-storage)

## 8. Scheduling, queues, background work
- Cron Jobs: up to 100/project on every plan; Hobby capped to once/day with UTC times accurate only to the hour, not the minute; Pro allows per-minute; failed invocations are not auto-retried. [Cron Jobs](https://vercel.com/docs/cron-jobs), [100/project change](https://vercel.com/changelog/cron-jobs-now-support-100-per-project-on-every-plan)
- `after()`/`waitUntil()`: run trailing work after the response is sent, capped by the invocation's own `maxDuration`, available on Node and Edge. [`after()`](https://nextjs.org/docs/app/api-reference/functions/after)
- Vercel Queues: managed at-least-once queue; failed handlers auto-retry; require producer idempotency keys and consumer-side dedupe. [Queues concepts](https://vercel.com/docs/queues/concepts)
- Vercel Workflows (`'use workflow'`): durable execution with no fixed duration cap, event-log replay on restart, encrypted step I/O — the documented answer for work exceeding `maxDuration`. [Workflows](https://vercel.com/docs/workflows)

## 9. Limits to check
- [Functions limits](https://vercel.com/docs/functions/limitations) · [Platform limits](https://vercel.com/docs/limits) · [Cron usage/pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing) · [Workflows pricing/limits](https://vercel.com/docs/workflows/pricing) · [CDN cache limits](https://vercel.com/docs/caching/cdn-cache#limits)

## 10. Deployment and verification surface
- `next dev` runs Functions/Middleware locally but doesn't reproduce multi-region routing, real CDN caching, Fluid compute's cross-invocation concurrency, Firewall/WAF, or actual cron firing — unverified specifics, inferred from architecture docs.
- `vercel dev` replicates more of the deployment environment, but Vercel recommends skipping it when your framework's own dev command suffices, i.e. it's not a full prod emulator. [`vercel dev`](https://vercel.com/docs/cli/dev)
- Preview Deployments are real, fully-built, network-reachable per-branch/PR deployments with their own env vars — the closest genuine pre-prod verification surface. [Environments](https://vercel.com/docs/deployments/environments)

## 11. Common false claims
- "Vercel Functions can't do WebSockets" — outdated; native support shipped in Public Beta June 2026 on Fluid compute. [WebSockets](https://vercel.com/docs/functions/websockets)
- "Vercel Postgres/KV are Vercel-managed databases" — both discontinued; migrated to Neon/Upstash, new ones are third-party Marketplace-provisioned. [Marketplace Storage](https://vercel.com/docs/marketplace-storage)
- "A Middleware auth check is sufficient" — Next.js calls this optimistic-only, and CVE-2025-29927 proved Middleware is bypassable via a spoofed header. [Data Security guide](https://nextjs.org/docs/app/guides/data-security)
- "ISR route-segment config is still the primary caching API" — Next.js 16 moved to `"use cache"`/`cacheLife`/`cacheTag` under Cache Components. [Migrating to Cache Components](https://nextjs.org/docs/app/guides/migrating-to-cache-components)
- "Edge Config is a general transactional database" — it's a read-optimized config store, not transactional. [Storage overview](https://vercel.com/docs/storage)

**As of 2026-09-26:** Next.js 16.3.x; Vercel Functions/Fluid compute docs (updated 2026-08-24); WebSockets docs (Public Beta, updated 2026-08-10); CDN Cache docs (updated 2026-09-14); Marketplace Storage, Workflows, Queues, Cron Jobs, and Environment Variables docs as currently published.
