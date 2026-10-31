'use strict';
// Witness R-1.15: A data file whose assignee has a control character is refused at load.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  for (const bad of ['a\tb', 'a\nb', 'a\u0001b', 'a\u007fb']) {
    const f = await L.seedFile((doc) => { doc.tickets[0].assignee = bad; });
    const r = await L.tryStart({ dataFile: f });
    check(!r.started, 'a data file with assignee ' + JSON.stringify(bad) + ' is refused at load');
  }
});
