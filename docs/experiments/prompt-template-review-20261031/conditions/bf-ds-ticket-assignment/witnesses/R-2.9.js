'use strict';
// Witness R-2.9: A non-string non-null value (array, object) answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  for (const v of [['dana'], {}, { name: 'dana' }]) {
    const r = await L.assign(s.api, t.id, v);
    check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'value ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
  }
});
