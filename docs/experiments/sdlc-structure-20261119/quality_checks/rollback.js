'use strict';
// For one ticket product: does a due time survive a rollback to 1.4.0 and the return, and does a huge hours setting
// start a service that then fails? Usage: node rollback.js <base tree> <product tree> [backfill script] [restore]
const fs = require('node:fs'); const os = require('node:os'); const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { start, req } = require('./lib');
const hours = (a, b) => (a && b ? (Date.parse(a) - Date.parse(b)) / 3600000 : null);
(async () => {
  const [base, dir, script, restore] = process.argv.slice(2);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qr-')); const out = {}; const file = path.join(tmp, 'data.json');
  const env = { DATA_FILE: file, DUE_TIMES: 'on' };
  const backfill = (extra = []) => {
    const r = spawnSync(process.execPath, [script, ...extra], { cwd: dir, env: { PATH: process.env.PATH, HOME: process.env.HOME, DATA_FILE: file }, encoding: 'utf8' });
    return `exit ${r.status} ${(r.stdout + r.stderr).trim().split('\n').pop().slice(0, 90)}`;
  };
  let s = await start(dir, 'src/server.js', env);
  if (!s.started) { out.first_start = 'did not start: ' + s.out().trim().split('\n').pop().slice(0, 120); console.log(JSON.stringify(out)); return; }
  const made = await req(s.port, 'POST', '/tickets', { title: 'Server room door', requester: 'ann@example.com', priority: 'urgent' });
  const t0 = made.body.ticket || made.body; out.created_hours = hours(t0.due, t0.created || t0.createdAt); const created = t0.created || t0.createdAt;
  await s.stop();
  const snapshot = path.join(tmp, 'pre-rollback.json'); fs.copyFileSync(file, snapshot);
  s = await start(base, 'src/server.js', { DATA_FILE: file });
  out.old_release_starts = s.started;
  if (s.started) {
    out.old_release_shows = (await req(s.port, 'GET', `/tickets/${t0.id}`)).status;
    out.old_release_patch = (await req(s.port, 'PATCH', `/tickets/${t0.id}`, { priority: 'low' })).status;
    await s.stop();
  }
  out.file_has_due_after_old_release = /"due"/.test(fs.readFileSync(file, 'utf8'));
  const after = path.join(tmp, 'after-rollback.json'); fs.copyFileSync(file, after);
  s = await start(dir, 'src/server.js', env);
  out.return_plain_start = s.started ? 'starts' : 'refuses: ' + s.out().trim().split('\n').pop().slice(0, 110);
  if (s.started) { const t = (await req(s.port, 'GET', `/tickets/${t0.id}`)).body; out.return_plain_hours = hours((t.ticket || t).due, created); await s.stop(); }
  if (script) {
    fs.copyFileSync(after, file); out.backfill = backfill();
    s = await start(dir, 'src/server.js', env);
    if (s.started) { const t = (await req(s.port, 'GET', `/tickets/${t0.id}`)).body; out.return_after_backfill_hours = hours((t.ticket || t).due, created); await s.stop(); } else out.return_after_backfill = 'refuses';
    if (restore) {
      fs.copyFileSync(after, file); out.restore = backfill(['--restore-from', snapshot]);
      s = await start(dir, 'src/server.js', env);
      if (s.started) { const t = (await req(s.port, 'GET', `/tickets/${t0.id}`)).body; out.return_after_restore_hours = hours((t.ticket || t).due, created); await s.stop(); } else out.return_after_restore = 'refuses';
    }
  }
  const f2 = path.join(tmp, 'huge.json');
  s = await start(dir, 'src/server.js', { DATA_FILE: f2, DUE_TIMES: 'on', DUE_HOURS_LOW: '2400000000' });
  out.huge_hours_start = s.started ? 'starts' : 'refuses';
  if (s.started) { out.huge_hours_create = (await req(s.port, 'POST', '/tickets', { title: 'x', requester: 'a@example.com', priority: 'low' })).status; await s.stop(); }
  console.log(JSON.stringify(out));
})();
