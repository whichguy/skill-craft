'use strict';
// Witness R-5.5: A closed ticket answers 409 conflict on assignment.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.advance(s.api, t.id, 'closed');
  const r = await L.assign(s.api, t.id, 'dana');
  check(r.status === 409 && r.body.error.code === 'conflict', 'closed ticket -> 409 conflict, got ' + r.status);
});
