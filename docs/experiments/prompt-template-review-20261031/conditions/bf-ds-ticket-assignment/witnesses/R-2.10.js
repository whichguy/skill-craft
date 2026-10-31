'use strict';
// Witness R-2.10: An unknown field answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await s.api.put('/tickets/' + t.id + '/assignee', { assignee: 'dana', extra: 1 });
  check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'unknown field -> 400 invalid, got ' + r.status);
  const g = await s.api.get('/tickets/' + t.id);
  check(g.body.assignee === null, 'nothing was assigned');
});
