'use strict';
// Witness R-8.1: Assigning enqueues an outbox event of type ticket.assigned.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const o = await L.outbox(s.api);
  const e = o.pending.filter((x) => x.type === 'ticket.assigned');
  eq(e.length, 1, 'one pending ticket.assigned event');
});
