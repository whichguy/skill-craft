'use strict';
// Witness R-2.6: An unknown ticket id answers 404 not_found.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const r = await L.assign(s.api, 'T-9999', 'dana');
  check(r.status === 404 && r.body && r.body.error && r.body.error.code === 'not_found', 'unknown id -> 404 not_found, got ' + r.status + ' ' + JSON.stringify(r.body));
});
