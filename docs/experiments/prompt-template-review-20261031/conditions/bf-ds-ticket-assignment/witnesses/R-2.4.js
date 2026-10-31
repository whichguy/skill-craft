'use strict';
// Witness R-2.4: Title, priority, requester and status keep their values.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api, { title: 'Keep me', priority: 'high', requester: 'sam' });
  const r = await L.assign(s.api, t.id, 'dana');
  const g = await s.api.get('/tickets/' + t.id);
  for (const f of ['title', 'priority', 'requester', 'status']) {
    eq(r.body[f], t[f], 'response ' + f);
    eq(g.body[f], t[f], 'GET ' + f);
  }
});
