'use strict';
// Witness R-5.2: An in_progress ticket accepts assignment.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.advance(s.api, t.id, 'in_progress');
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 200 && r.body.assignee === 'dana', 'in_progress ticket accepts assignment, got ' + r.status);
});
