'use strict';

const { AppError, NotFoundError } = require('./errors');
const { actorOf, readJson, sendError, sendJson } = require('./http');
const { Router } = require('./router');
const { parseListQuery } = require('./tickets/query');
const validate = require('./tickets/validate');

/**
 * The HTTP API (docs/api.md), as a request listener for http.createServer.
 *
 * A handler reads and validates the request, calls one store method and returns { status, body }. Handlers never
 * change a ticket, the audit log or the outbox themselves, and never call the notifier (CONTRIBUTING.md). Anything a
 * handler throws is answered in the error envelope.
 */
function createApp({ store, maxBodyBytes = 64 * 1024, log, logRequests = false }) {
  const router = new Router();
  const body = (req) => readJson(req, { limit: maxBodyBytes });

  router.get('/health', () => ({ status: 200, body: { status: 'ok' } }));

  router.get('/tickets', ({ url }) => ({ status: 200, body: store.list(parseListQuery(url.searchParams)) }));

  router.post('/tickets', async ({ req }) => {
    const input = validate.newTicket(await body(req));
    return { status: 201, body: store.create(input, actorOf(req)) };
  });

  router.get('/tickets/:id', ({ params }) => ({ status: 200, body: store.get(params.id) }));

  router.patch('/tickets/:id', async ({ req, params }) => {
    const patch = validate.ticketPatch(await body(req));
    return { status: 200, body: store.update(params.id, patch, actorOf(req)) };
  });

  router.post('/tickets/:id/transition', async ({ req, params }) => {
    const to = validate.transition(await body(req));
    return { status: 200, body: store.transition(params.id, to, actorOf(req)) };
  });

  router.get('/tickets/:id/audit', ({ params }) => ({ status: 200, body: { items: store.history(params.id) } }));

  // Operations: what the outbox holds. Served on the internal network only, like the rest of the service.
  router.get('/admin/outbox', () => ({ status: 200, body: store.outboxReport() }));

  return async function handle(req, res) {
    const started = process.hrtime.bigint();
    let status;
    try {
      const url = new URL(req.url, 'http://localhost');
      const route = router.match(req.method, url.pathname);
      if (!route) throw notFound(router, req.method, url.pathname);
      const result = await route.handler({ req, url, params: route.params });
      sendJson(res, result.status, result.body);
      status = result.status;
    } catch (error) {
      if (!(error instanceof AppError)) log.error(`${req.method} ${req.url} failed`, error);
      status = sendError(res, error);
    } finally {
      if (logRequests) log.request(req, status, Number(process.hrtime.bigint() - started) / 1e6);
    }
  };
}

function notFound(router, method, pathname) {
  const methods = router.methodsFor(pathname);
  const message = methods.length
    ? `${pathname} does not answer ${method}; it answers ${methods.join(', ')}`
    : `no route for ${method} ${pathname}`;
  return new NotFoundError(message);
}

module.exports = { createApp };
