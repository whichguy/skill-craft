'use strict';
// Witness R-9.9: A whitespace-only assignee filter answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  await L.ticket(s.api);
  for (const q of ['%20', '%20%20%20']) {
    const r = await s.api.get('/tickets?assignee=' + q);
    check(r.status === 400 && r.body.error.code === 'invalid', 'whitespace-only filter ' + q + ' -> 400 invalid, got ' + r.status);
  }
});
