'use strict';
// Witness R-7.1: A real assignment appends an audit entry with action ticket.assigned.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const a = (await L.auditOf(s.api, t.id)).filter((e) => e.action === 'ticket.assigned');
  eq(a.length, 1, 'one ticket.assigned entry');
});
