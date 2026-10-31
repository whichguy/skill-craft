'use strict';
// Witness R-3.2: After the unassigning PUT the ticket reads back with assignee null.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, null);
  const g = await s.api.get('/tickets/' + t.id);
  check(g.body.assignee === null, 'reads back null, got ' + JSON.stringify(g.body.assignee));
});
