'use strict';
// Witness R-1.10: With DATA_FILE a restarted service returns the same assignee.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = L.tmpfile('d.json');
  let s = await L.startService({ dataFile: f });
  const t = await L.ticket(s.api);
  await L.assign(s.api, t.id, 'dana');
  await s.stop();
  s = await L.startService({ dataFile: f });
  const r = await s.api.get('/tickets/' + t.id);
  eq(r.body.assignee, 'dana', 'assignee after restart');
});
