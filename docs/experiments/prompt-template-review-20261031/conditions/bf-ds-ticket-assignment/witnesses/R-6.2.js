'use strict';
// Witness R-6.2: Assigning the current agent adds no audit entry.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const before = await L.auditOf(s.api, t.id);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200, 'answers 200');
  eq(await L.auditOf(s.api, t.id), before, 'audit log unchanged');
});
