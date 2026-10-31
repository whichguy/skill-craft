'use strict';
// Witness R-7.3: Assigning dana to an unassigned ticket records {assignee:{from:null,to:dana}}.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
  eq(e && e.changes, { assignee: { from: null, to: 'dana' } }, 'changes of the assignment entry');
});
