'use strict';
// Witness R-3.3: Unassigning an already unassigned ticket is accepted (200).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, null);
  check(r.status === 200, 'unassign of an unassigned ticket answers 200, got ' + r.status);
});
