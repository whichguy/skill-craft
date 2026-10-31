'use strict';
// Witness R-8.9: Unassigning enqueues nothing.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const before = await L.events(s.api);
  await L.assign(s.api, t.id, null);
  const after = await L.events(s.api);
  eq(after.length, before.length, 'no event added by unassigning');
});
