'use strict';
// Witness R-6.5: Unassigning an unassigned ticket answers 200 and leaves audit and outbox unchanged.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const auditBefore = await L.auditOf(s.api, t.id);
  const outboxBefore = await L.outbox(s.api);
  const r = await L.assign(s.api, t.id, null);
  check(r.status === 200 && r.body.assignee === null, 'answers 200 with the unchanged ticket, got ' + r.status);
  eq(await L.auditOf(s.api, t.id), auditBefore, 'audit unchanged');
  eq(await L.outbox(s.api), outboxBefore, 'outbox unchanged');
});
