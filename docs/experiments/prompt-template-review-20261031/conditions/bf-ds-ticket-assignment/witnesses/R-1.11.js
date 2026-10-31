'use strict';
// Witness R-1.11: A version-1 file without assignee loads the tickets with assignee: null.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = await L.seedFile((doc) => { for (const t of doc.tickets) delete t.assignee; });
  const s = await L.startService({ dataFile: f });
  const r = await s.api.get('/tickets/T-0001');
  check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'legacy ticket loads with assignee: null');
});
