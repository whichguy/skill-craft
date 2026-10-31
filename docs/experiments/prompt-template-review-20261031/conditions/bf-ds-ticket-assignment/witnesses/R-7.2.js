'use strict';
// Witness R-7.2: A real assignment appends exactly one audit entry.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const before = (await L.auditOf(s.api, t.id)).length;
  await L.assign(s.api, t.id, 'dana');
  eq((await L.auditOf(s.api, t.id)).length, before + 1, 'exactly one new audit entry');
});
