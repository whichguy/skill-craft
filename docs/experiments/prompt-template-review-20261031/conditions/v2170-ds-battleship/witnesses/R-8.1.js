'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const child = L.cp.spawn(process.execPath, ['-e', "require('./battleship.js'); setTimeout(() => {}, 1500);"], { cwd: L.WORK, stdio: 'ignore' });
  let code = 'running';
  child.once('exit', (c) => { code = c; });
  await L.sleep(700);
  const ports = L.lsofPorts(child.pid);
  check(ports.length === 0, 'requiring battleship.js opened listening sockets: ' + ports);
  await L.sleep(1800);
  check(code === 0, 'the process did not exit normally (exit ' + code + ')');
  if (code === 'running') child.kill('SIGKILL');
});
