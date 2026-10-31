'use strict';
// Witness R-2.8: A missing assignee field answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await s.api.put('/tickets/' + t.id + '/assignee', {});
  check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'missing field -> 400 invalid, got ' + r.status);
});
