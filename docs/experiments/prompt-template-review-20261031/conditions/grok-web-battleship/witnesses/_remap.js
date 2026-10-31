'use strict';
// Preload for witnesses only: when the server asks to listen on a shared port (3000, 3456), listen on a
// port from our range instead and log what was requested, so a witness never binds a shared port.
const net = require('node:net');
const fs = require('node:fs');
const map = new Map((process.env.REMAP || '').split(',').filter(Boolean).map((p) => p.split(':').map(Number)));
const log = process.env.REMAP_LOG;
const orig = net.Server.prototype.listen;
net.Server.prototype.listen = function (...args) {
  let port = args[0];
  let host = typeof args[1] === 'string' ? args[1] : undefined;
  if (port && typeof port === 'object') { host = port.host; port = port.port; }
  if (log) fs.appendFileSync(log, JSON.stringify({ port: Number(port), host }) + '\n');
  if (map.has(Number(port))) {
    const to = map.get(Number(port));
    if (args[0] && typeof args[0] === 'object') args[0] = { ...args[0], port: to }; else args[0] = to;
  }
  return orig.apply(this, args);
};
