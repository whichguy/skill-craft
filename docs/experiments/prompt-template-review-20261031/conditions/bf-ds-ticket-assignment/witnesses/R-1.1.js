'use strict';
// Witness R-1.1: POST /tickets answers 201 with assignee: null (key present).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const r = await s.api.post('/tickets', L.NEW);
  check(r.status === 201, 'create answers 201');
  check('assignee' in r.body && r.body.assignee === null, 'POST /tickets body carries assignee: null');
});
