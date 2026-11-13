'use strict';

/**
 * What the tests share: the service on a free port with the worker off, a JSON client for it, and a ticket body.
 */

const http = require('node:http');
const { manualClock } = require('../src/clock');
const { silentLogger } = require('../src/log');
const { createService } = require('../src/server');

/** The settings a test service starts with: port 0, memory only, the worker off. */
const TEST_SETTINGS = Object.freeze({
  port: 0,
  dataFile: null,
  notifyFile: null,
  workerIntervalMs: 0,
  maxBodyBytes: 64 * 1024,
  logRequests: false,
});

/** Start a service with `settings` over TEST_SETTINGS, run `fn(api, service)`, and stop it whatever happens. */
async function withService(settings, fn) {
  const { clock = manualClock(), ...config } = settings;
  const service = createService({ ...TEST_SETTINGS, ...config }, { clock, log: silentLogger });
  const port = await service.start();
  const api = client(`http://127.0.0.1:${port}`);
  try {
    return await fn(api, service);
  } finally {
    api.close();
    await hungUp(service.server);
    await service.stop();
  }
}

/** Wait (a second at most) until the server has seen its clients hang up, so it never closes a connection itself. */
async function hungUp(server) {
  const end = Date.now() + 1000;
  while (Date.now() < end) {
    const open = await new Promise((resolve) => server.getConnections((error, count) => resolve(error ? 0 : count)));
    if (open === 0) return;
    await new Promise((resolve) => setTimeout(resolve, 2));
  }
}

/**
 * A JSON client: each call resolves to { status, body, headers } with the body parsed (null when empty). Each client has an
 * agent of its own, closed with close(): a later test's server can be given the port an earlier one closed, and a connection
 * kept alive for the old server must never carry a request to the new one.
 */
function client(base) {
  const { hostname, port } = new URL(base);
  const agent = new http.Agent({ keepAlive: true });
  function call(method, path, body, headers = {}) {
    const payload = body === undefined ? null : Buffer.from(typeof body === 'string' ? body : JSON.stringify(body));
    const sent = { ...headers, ...(payload ? { 'content-type': 'application/json', 'content-length': payload.length } : {}) };
    return new Promise((resolve, reject) => {
      const req = http.request({ hostname, port, path, method, headers: sent, agent }, (res) => {
        const chunks = [];
        res.on('data', (chunk) => chunks.push(chunk));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          resolve({ status: res.statusCode, body: text ? JSON.parse(text) : null, headers: res.headers });
        });
        res.on('error', reject);
      });
      req.on('error', reject);
      req.end(payload);
    });
  }
  return {
    base,
    get: (path, headers) => call('GET', path, undefined, headers),
    post: (path, body, headers) => call('POST', path, body, headers),
    put: (path, body, headers) => call('PUT', path, body, headers),
    patch: (path, body, headers) => call('PATCH', path, body, headers),
    delete: (path, headers) => call('DELETE', path, undefined, headers),
    close: () => agent.destroy(),
  };
}

/** A body for POST /tickets, with `overrides`. */
function ticketBody(overrides = {}) {
  return { title: 'Printer on the 4th floor jams', requester: 'maria@example.com', priority: 'normal', ...overrides };
}

module.exports = { TEST_SETTINGS, client, ticketBody, withService };
