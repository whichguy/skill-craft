'use strict';
// Witness R-5.3: Open and in_progress tickets accept unassignment.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const a = await L.ticket(s.api);
  await L.assign(s.api, a.id, 'dana');
  let r = await L.assign(s.api, a.id, null);
  check(r.status === 200 && r.body.assignee === null, 'open ticket accepts unassignment, got ' + r.status);
  await L.assign(s.api, a.id, 'dana');
  await L.advance(s.api, a.id, 'in_progress');
  r = await L.assign(s.api, a.id, null);
  check(r.status === 200 && r.body.assignee === null, 'in_progress ticket accepts unassignment, got ' + r.status);
});
