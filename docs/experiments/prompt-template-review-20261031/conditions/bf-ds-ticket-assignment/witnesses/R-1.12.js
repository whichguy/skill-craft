'use strict';
// Witness R-1.12: A data file with a non-string assignee is refused at load with a message naming the record.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const f = await L.seedFile((doc) => { doc.tickets[0].assignee = 42; });
  const r = await L.tryStart({ dataFile: f });
  check(!r.started, 'a data file with assignee 42 is refused at load');
  check(/tickets\[0\]|T-0001/.test(r.stderr.replace(f, '')), 'the refusal names the record, got: ' + r.stderr.trim());
});
