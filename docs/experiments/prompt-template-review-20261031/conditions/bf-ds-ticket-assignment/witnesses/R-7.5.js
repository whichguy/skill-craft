'use strict';
// Witness R-7.5: Reassigning dana to erin records {from:dana,to:erin}.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await L.assign(s.api, t.id, 'erin');
  const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
  eq(a[1] && a[1].changes, { assignee: { from: 'dana', to: 'erin' } }, 'reassignment entry');
});
