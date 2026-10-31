'use strict';
// Witness R-4.2: A 64-character name is accepted.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const name = 'n'.repeat(64);
  const r = await L.assign(s.api, t.id, name);
  check(r.status === 200 && r.body.assignee === name, '64-character name accepted, got ' + r.status);
});
