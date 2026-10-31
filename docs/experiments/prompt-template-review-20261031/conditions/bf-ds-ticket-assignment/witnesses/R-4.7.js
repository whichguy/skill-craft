'use strict';
// Witness R-4.7: A name with a line break is refused with 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  for (const v of ['one\ntwo', 'one\rtwo', 'one\r\ntwo']) {
    const r = await L.assign(s.api, t.id, v);
    check(r.status === 400 && r.body.error.code === 'invalid', 'line break ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
  }
});
