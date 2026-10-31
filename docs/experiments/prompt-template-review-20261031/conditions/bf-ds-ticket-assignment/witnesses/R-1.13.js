'use strict';
// Witness R-1.13: A data file with an empty-string assignee is refused at load.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = await L.seedFile((doc) => { doc.tickets[0].assignee = ''; });
  const r = await L.tryStart({ dataFile: f });
  check(!r.started, 'a data file with assignee "" is refused at load');
});
