'use strict';
// Witness R-5.1: An open ticket accepts assignment.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200 && r.body.assignee === 'dana', 'open ticket accepts assignment, got ' + r.status);
});
