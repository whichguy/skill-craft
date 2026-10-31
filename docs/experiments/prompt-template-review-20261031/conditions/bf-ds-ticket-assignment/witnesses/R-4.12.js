'use strict';
// Witness R-4.12: The 400 message for an invalid assignee names assignee.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  for (const v of ['', 42, 'n'.repeat(65), 'a\tb', true]) {
    const r = await L.assign(s.api, t.id, v);
    check(r.status === 400 && /assignee/.test(r.body.error.message), 'message for ' + JSON.stringify(v).slice(0, 20) + ' names assignee: ' + (r.body && r.body.error && r.body.error.message));
  }
});
