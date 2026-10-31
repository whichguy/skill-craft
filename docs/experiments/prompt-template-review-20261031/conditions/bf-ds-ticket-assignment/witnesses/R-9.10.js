'use strict';
// Witness R-9.10: An assignee filter longer than 64 characters answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  await L.ticket(s.api);
  const r = await s.api.get('/tickets?assignee=' + 'n'.repeat(65));
  check(r.status === 400 && r.body.error.code === 'invalid', '65-character filter -> 400 invalid, got ' + r.status);
});
