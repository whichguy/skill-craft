'use strict';
// Witness R-5.6: A refused assignment leaves the assignee unchanged.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  for (const final of ['resolved', 'closed']) {
    const t = await L.ticket(s.api, { title: 'T ' + final });
    await L.assign(s.api, t.id, 'dana');
    await L.advance(s.api, t.id, final);
    const r = await L.assign(s.api, t.id, 'erin');
    check(r.status === 409, final + ' ticket refuses assignment');
    const g = await s.api.get('/tickets/' + t.id);
    eq(g.body.assignee, 'dana', final + ' ticket keeps its assignee');
  }
});
