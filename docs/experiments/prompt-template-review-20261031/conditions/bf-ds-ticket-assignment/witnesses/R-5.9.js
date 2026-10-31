'use strict';
// Witness R-5.9: {assignee:null} on a resolved/closed ticket answers 409 and changes nothing.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  for (const final of ['resolved', 'closed']) {
    const t = await L.ticket(s.api, { title: 'T ' + final });
    await L.assign(s.api, t.id, 'dana');
    await L.advance(s.api, t.id, final);
    const r = await L.assign(s.api, t.id, null);
    check(r.status === 409 && r.body.error.code === 'conflict', final + ' ticket unassign -> 409 conflict, got ' + r.status);
    const g = await s.api.get('/tickets/' + t.id);
    eq(g.body.assignee, 'dana', final + ' keeps assignee');
  }
});
