'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
function expectPort(r, port, label) {
  const ok = (r.kind === 'listening' && r.ports.includes(port))
    || (r.kind === 'refused' && r.port === port)
    || (r.kind === 'died' && new RegExp('127\\.0\\.0\\.1:' + port + '\\b').test(r.err));
  check(ok, label + ': expected the server to listen on (or be refused on) ' + port + ', got ' + JSON.stringify({ kind: r.kind, ports: r.ports, port: r.port, out: r.out.slice(0, 120), err: r.err.slice(0, 160) }));
}
L.run(async () => {
const r = await L.listenReport('70000');
expectPort(r, 3000, 'PORT=70000');
});
