'use strict';
// Witness R-1.6: The data file's ticket record carries an assignee key (null when unassigned).
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = L.tmpfile('d.json');
  const s = await L.startService({ dataFile: f });
  const t = await L.ticket(s.api);
  let doc = L.readJson(f);
  check('assignee' in doc.tickets[0] && doc.tickets[0].assignee === null, 'data file ticket record has assignee: null');
  await L.assign(s.api, t.id, 'dana');
  doc = L.readJson(f);
  eq(doc.tickets[0].assignee, 'dana', 'data file holds the assigned name');
});
