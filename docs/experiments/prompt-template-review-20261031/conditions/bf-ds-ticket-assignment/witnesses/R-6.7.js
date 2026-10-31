'use strict';
// Witness R-6.7: Assigning the current agent with surrounding whitespace is also a no-op.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const a = await L.assign(s.api, t.id, 'dana');
  const auditBefore = await L.auditOf(s.api, t.id);
  const outboxBefore = await L.outbox(s.api);
  await sleep(30);
  const r = await L.assign(s.api, t.id, ' dana ');
  check(r.status === 200 && r.body.assignee === 'dana', 'answers 200 with dana');
  eq(r.body.updated, a.body.updated, 'updated unchanged');
  eq(await L.auditOf(s.api, t.id), auditBefore, 'audit unchanged');
  eq(await L.outbox(s.api), outboxBefore, 'outbox unchanged');
});
