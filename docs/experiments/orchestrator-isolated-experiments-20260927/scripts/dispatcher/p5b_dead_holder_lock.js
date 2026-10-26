'use strict';
// P5b (adapted P5): the orphan lock written in the current holder format
// ({pid, host} JSON, as state.js lockHolder writes it) for a dead local PID. Original P5 wrote a bare "999999".
const fs = require('fs'); const os = require('os'); const path = require('path'); const lib = require('./lib');
const {spawnSync} = require('child_process');
const dead = spawnSync(process.execPath, ['-e', 'process.stdout.write(String(process.pid))'], {encoding: 'utf8'}).stdout;
for (const [label, bytes] of [['dead local pid (current format)', JSON.stringify({pid: Number(dead), host: os.hostname()})],
                              ['bare pid (original P5 format)', '999999'],
                              ['live pid other host', JSON.stringify({pid: process.pid, host: 'elsewhere.example'})]]) {
  const {dir} = lib.initRun();
  fs.writeFileSync(path.join(dir, '.dispatcher.lock'), bytes);
  const t = Date.now();
  const c = lib.cli('claim', dir, {owner: 'parent', steps: ['A']});
  console.log(label, '-> claim status', c.status, (Date.now() - t) + 'ms', c.status ? c.stderr.trim().slice(0, 220) : 'lock present after: ' + fs.existsSync(path.join(dir, '.dispatcher.lock')));
}
// live local holder: claim should wait up to LOCK_WAIT_MS and then succeed once released
{
  const {dir} = lib.initRun();
  const lock = path.join(dir, '.dispatcher.lock');
  fs.writeFileSync(lock, JSON.stringify({pid: process.pid, host: os.hostname()}));
  const child = require('child_process').spawn(process.execPath, ['-e', `setTimeout(()=>require('fs').unlinkSync(${JSON.stringify(lock)}),800)`]);
  const t = Date.now();
  const c = spawnSync(process.execPath, [lib.HELPER, 'claim', dir, lib.save({owner: 'parent', steps: ['A']})], {cwd: lib.CWD, encoding: 'utf8'});
  console.log('live local holder released after 800ms -> claim status', c.status, (Date.now() - t) + 'ms');
}
