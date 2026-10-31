'use strict';
// Witness R-9.8: A filtered listing pages through its cursors without duplicates or gaps.
const L = require('./_lib');
const { check, eq, sleep } = L;
L.run(async () => {
  const s = await L.startService();
  const mine = [];
  for (let i = 0; i < 6; i += 1) {
    const t = await L.ticket(s.api, { title: 'T' + i });
    if (i % 3 !== 2) { await L.assign(s.api, t.id, 'dana'); mine.push(t.id); } else { await L.assign(s.api, t.id, 'erin'); }
  }
  const got = [];
  let url = '/tickets?assignee=dana&limit=2';
  for (let page = 0; page < 20; page += 1) {
    const r = await s.api.get(url);
    check(r.status === 200, 'page answers 200');
    got.push(...r.body.items.map((i) => i.id));
    if (!r.body.next) break;
    url = '/tickets?assignee=dana&limit=2&cursor=' + encodeURIComponent(r.body.next);
  }
  eq(got, mine, 'every dana ticket exactly once, in order');
});
