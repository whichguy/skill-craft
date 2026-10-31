'use strict';
// Witness R-4.3: An empty string is refused with 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, '');
  check(r.status === 400 && r.body.error.code === 'invalid', 'empty name -> 400 invalid, got ' + r.status);
});
