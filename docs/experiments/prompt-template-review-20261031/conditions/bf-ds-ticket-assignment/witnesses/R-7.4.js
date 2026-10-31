'use strict';
// Witness R-7.4: Unassigning records {assignee:{from:dana,to:null}} under ticket.assigned.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, null);
  const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
  eq(a.length, 2, 'two assignment entries');
  eq(a[1] && a[1].changes, { assignee: { from: 'dana', to: null } }, 'unassignment entry');
});
