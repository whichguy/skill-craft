'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

const envelope = (response, status, code) => {
  assert.equal(response.status, status, JSON.stringify(response.body));
  assert.equal(response.body.error.code, code);
  assert.equal(typeof response.body.error.message, 'string');
};

describe('POST /tickets', () => {
  test('creates an open ticket and answers 201 with it', async () => {
    await withService({}, async (api) => {
      const { status, body } = await api.post('/tickets', ticketBody({ priority: 'high' }));
      assert.equal(status, 201);
      assert.equal(body.id, 'T-0001');
      assert.equal(body.status, 'open');
      assert.equal(body.priority, 'high');
      assert.deepEqual((await api.get('/tickets/T-0001')).body, body);
    });
  });

  test('answers a bad body with 400 invalid', async () => {
    await withService({}, async (api) => {
      envelope(await api.post('/tickets', '{"title":'), 400, 'invalid');
      envelope(await api.post('/tickets', ticketBody({ title: '' })), 400, 'invalid');
      envelope(await api.post('/tickets', ticketBody({ owner: 'dana' })), 400, 'invalid');
      envelope(await api.post('/tickets', []), 400, 'invalid');
    });
  });

  test('refuses a body over MAX_BODY_BYTES', async () => {
    await withService({ maxBodyBytes: 1024 }, async (api) => {
      envelope(await api.post('/tickets', ticketBody({ title: 'x'.repeat(2000) })), 400, 'invalid');
    });
  });
});

describe('GET /tickets/:id', () => {
  test('answers 404 not_found for a ticket that does not exist', async () => {
    await withService({}, async (api) => {
      envelope(await api.get('/tickets/T-0042'), 404, 'not_found');
      envelope(await api.get('/tickets/42'), 404, 'not_found');
    });
  });
});

describe('PATCH /tickets/:id', () => {
  test('changes the priority and records who did it', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody());
      const { status, body } = await api.patch('/tickets/T-0001', { priority: 'urgent' }, { 'X-Actor': 'sam' });
      assert.equal(status, 200);
      assert.equal(body.priority, 'urgent');
      const history = (await api.get('/tickets/T-0001/audit')).body.items;
      assert.deepEqual(history.at(-1).changes, { priority: { from: 'normal', to: 'urgent' } });
      assert.equal(history.at(-1).actor, 'sam');
    });
  });

  test('answers 409 conflict for a closed ticket', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody());
      for (const to of ['in_progress', 'resolved', 'closed']) await api.post('/tickets/T-0001/transition', { to });
      envelope(await api.patch('/tickets/T-0001', { title: 'Reworded' }), 409, 'conflict');
    });
  });
});

describe('POST /tickets/:id/transition', () => {
  test('moves the ticket and answers it', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody());
      const { status, body } = await api.post('/tickets/T-0001/transition', { to: 'in_progress' });
      assert.equal(status, 200);
      assert.equal(body.status, 'in_progress');
    });
  });

  test('answers 409 for a move the lifecycle does not allow and 400 for a status that does not exist', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody());
      envelope(await api.post('/tickets/T-0001/transition', { to: 'closed' }), 409, 'conflict');
      envelope(await api.post('/tickets/T-0001/transition', { to: 'done' }), 400, 'invalid');
      envelope(await api.post('/tickets/T-0099/transition', { to: 'in_progress' }), 404, 'not_found');
    });
  });
});

describe('GET /tickets', () => {
  async function seed(api) {
    const rows = [['open', 'low'], ['in_progress', 'urgent'], ['open', 'urgent'], ['resolved', 'high'], ['open', 'normal']];
    for (const [status, priority] of rows) {
      const { body } = await api.post('/tickets', ticketBody({ priority }));
      const path = { open: [], in_progress: ['in_progress'], resolved: ['in_progress', 'resolved'] }[status];
      for (const to of path) await api.post(`/tickets/${body.id}/transition`, { to });
    }
  }
  const ids = (response) => response.body.items.map((ticket) => ticket.id);

  test('lists every ticket in id order, 20 to a page', async () => {
    await withService({}, async (api) => {
      for (let n = 0; n < 23; n += 1) await api.post('/tickets', ticketBody());
      const first = await api.get('/tickets');
      assert.equal(first.status, 200);
      assert.equal(first.body.items.length, 20);
      assert.equal(first.body.items[0].id, 'T-0001');
      const second = await api.get(`/tickets?cursor=${first.body.next}`);
      assert.deepEqual(ids(second), ['T-0021', 'T-0022', 'T-0023']);
      assert.equal(second.body.next, null);
    });
  });

  test('filters by status', async () => {
    await withService({}, async (api) => {
      await seed(api);
      assert.deepEqual(ids(await api.get('/tickets?status=open')), ['T-0001', 'T-0003', 'T-0005']);
      assert.deepEqual(ids(await api.get('/tickets?status=closed')), []);
    });
  });

  test('filters by priority', async () => {
    await withService({}, async (api) => {
      await seed(api);
      assert.deepEqual(ids(await api.get('/tickets?priority=urgent')), ['T-0002', 'T-0003']);
    });
  });

  test('pages a filtered listing through its cursors', async () => {
    await withService({}, async (api) => {
      await seed(api);
      const first = await api.get('/tickets?status=open&limit=2');
      assert.deepEqual(ids(first), ['T-0001', 'T-0003']);
      const second = await api.get(`/tickets?status=open&limit=2&cursor=${first.body.next}`);
      assert.deepEqual(ids(second), ['T-0005']);
      assert.equal(second.body.next, null);
    });
  });

  test('answers a bad filter, limit or cursor with 400 invalid', async () => {
    await withService({}, async (api) => {
      for (const query of ['status=done', 'priority=critical', 'limit=0', 'limit=101', 'limit=x', 'cursor=abc']) {
        envelope(await api.get(`/tickets?${query}`), 400, 'invalid');
      }
    });
  });
});

describe('GET /tickets/:id/audit', () => {
  test('records the X-Actor of each change, and system without one', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody(), { 'X-Actor': 'dana' });
      await api.post('/tickets/T-0001/transition', { to: 'in_progress' });
      const { status, body } = await api.get('/tickets/T-0001/audit');
      assert.equal(status, 200);
      assert.deepEqual(body.items.map((entry) => [entry.seq, entry.action, entry.actor]), [
        [1, 'ticket.created', 'dana'],
        [2, 'ticket.transitioned', 'system'],
      ]);
      envelope(await api.get('/tickets/T-0002/audit'), 404, 'not_found');
    });
  });

  test('refuses an X-Actor over 64 characters', async () => {
    await withService({}, async (api) => {
      envelope(await api.post('/tickets', ticketBody(), { 'X-Actor': 'a'.repeat(65) }), 400, 'invalid');
    });
  });
});

describe('GET /admin/outbox', () => {
  test('shows what changes enqueued, pending while the worker is off', async () => {
    await withService({}, async (api) => {
      await api.post('/tickets', ticketBody());
      for (const to of ['in_progress', 'resolved']) await api.post('/tickets/T-0001/transition', { to });
      const { status, body } = await api.get('/admin/outbox');
      assert.equal(status, 200);
      assert.deepEqual(body.pending.map((event) => [event.type, event.to, event.ticket]), [
        ['ticket.created', 'maria@example.com', 'T-0001'],
        ['ticket.resolved', 'maria@example.com', 'T-0001'],
      ]);
      assert.deepEqual([body.sent, body.dead], [[], []]);
    });
  });
});

describe('everything else', () => {
  test('answers 404 not_found for an unknown route or method', async () => {
    await withService({}, async (api) => {
      envelope(await api.get('/nowhere'), 404, 'not_found');
      envelope(await api.delete('/tickets/T-0001'), 404, 'not_found');
      assert.deepEqual((await api.get('/health')).body, { status: 'ok' });
    });
  });
});
