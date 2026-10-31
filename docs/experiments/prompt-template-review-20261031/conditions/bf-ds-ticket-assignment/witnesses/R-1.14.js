'use strict';
// Witness R-1.14: A data file with a 65-character assignee is refused at load.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = await L.seedFile((doc) => { doc.tickets[0].assignee = 'x'.repeat(65); });
  const r = await L.tryStart({ dataFile: f });
  check(!r.started, 'a data file with a 65-character assignee is refused at load');
});
