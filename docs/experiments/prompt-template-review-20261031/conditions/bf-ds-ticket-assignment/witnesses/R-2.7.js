'use strict';
// Witness R-2.7: A body that is not a JSON object answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  for (const raw of ['[]', '"dana"', '42', 'null']) {
    const r = await s.api.putRaw('/tickets/' + t.id + '/assignee', raw);
    check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'body ' + raw + ' -> 400 invalid, got ' + r.status);
  }
});
