'use strict';
// Witness R-7.9: GET audit returns the assignment entries oldest first.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await sleep(10);
  await L.assign(s.api, t.id, 'erin');
  const a = await L.auditOf(s.api, t.id);
  eq(a.map((x) => x.action), ['ticket.created', 'ticket.assigned', 'ticket.assigned'], 'actions in order');
  eq(a.map((x) => x.seq), [...a.map((x) => x.seq)].sort((x, y) => x - y), 'seq ascending');
  eq(a.slice(1).map((x) => x.changes.assignee.to), ['dana', 'erin'], 'dana before erin');
});
