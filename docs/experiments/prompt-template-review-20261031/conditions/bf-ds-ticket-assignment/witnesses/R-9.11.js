'use strict';
// Witness R-9.11: An assignee filter with a control character answers 400 invalid.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  await L.ticket(s.api);
  for (const q of ['a%09b', 'a%0Ab', 'a%01b', 'a%7Fb']) {
    const r = await s.api.get('/tickets?assignee=' + q);
    check(r.status === 400 && r.body.error.code === 'invalid', 'control-character filter ' + q + ' -> 400 invalid, got ' + r.status);
  }
});
