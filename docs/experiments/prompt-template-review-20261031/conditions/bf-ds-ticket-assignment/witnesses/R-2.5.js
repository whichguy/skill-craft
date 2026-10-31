'use strict';
// Witness R-2.5: The agent name is taken after trimming.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  const r = await L.assign(s.api, t.id, '  dana  ');
  check(r.status === 200, 'padded name accepted');
  eq(r.body.assignee, 'dana', 'response is trimmed');
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.assignee, 'dana', 'GET is trimmed');
});
