'use strict';
// Witness R-7.6: The audit entry's actor is the X-Actor header.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana', { 'x-actor': 'alice' });
  const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
  eq(e && e.actor, 'alice', 'actor');
});
