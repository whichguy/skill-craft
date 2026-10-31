'use strict';
// Witness R-8.6: A->B->A still records the last change in the audit log.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, 'erin');
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200 && r.body.assignee === 'dana', 'ticket is back with dana');
  const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
  eq(a.length, 3, 'three assignment entries');
  eq(a[2] && a[2].changes, { assignee: { from: 'erin', to: 'dana' } }, 'the return is audited');
});
