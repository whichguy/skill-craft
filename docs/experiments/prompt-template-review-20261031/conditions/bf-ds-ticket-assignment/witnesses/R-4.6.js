'use strict';
// Witness R-4.6: A name with a tab is refused with 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, 'one\ttwo');
  check(r.status === 400 && r.body.error.code === 'invalid', 'tab -> 400 invalid, got ' + r.status);
});
