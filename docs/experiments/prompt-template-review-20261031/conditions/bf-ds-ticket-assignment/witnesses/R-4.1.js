'use strict';
// Witness R-4.1: A one-character name is accepted.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, 'a');
  check(r.status === 200 && r.body.assignee === 'a', 'name "a" accepted, got ' + r.status);
});
