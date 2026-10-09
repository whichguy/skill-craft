// A Node preload for the quality phase's children: no process in the tree may listen on, or connect to, a port the case declares.
//
// A delivered product defaults to the port its prompt names (3000) and a mutant of the line that reads PORT, or of the guard that
// keeps a server from starting under test, listens there whatever PORT says. It would answer a sibling case's or a sibling model's
// request on that port, and a held port would read as a caught mutant. The refusal is the one an occupied or closed port gives
// (EADDRINUSE on listen, ECONNREFUSED on connect) and every refusal appends one line, `<pid> listen|connect <port>`, to
// $SHIPLOOP_E2E_REFUSE_LOG so the harness can count them. $SHIPLOOP_E2E_REFUSE_PORTS is a comma-separated list.
//
// Loaded with NODE_OPTIONS=--require, so children of a test run (a spawned `node server.js`) inherit it.
'use strict';
const net = require('net');
const fs = require('fs');

const ports = new Set((process.env.SHIPLOOP_E2E_REFUSE_PORTS || '').split(',').filter(Boolean).map(Number));
const log = process.env.SHIPLOOP_E2E_REFUSE_LOG;

function note(kind, port) {
  if (!log) return;
  try { fs.appendFileSync(log, `${process.pid} ${kind} ${port}\n`); } catch (_) { /* a log that cannot be written must not change a run */ }
}

// The port a call names: a number, a numeric string, or an options object with a port; undefined for a path, a handle or nothing.
function portOf(first) {
  let value = first;
  if (value && typeof value === 'object' && !Array.isArray(value)) value = value.port;
  if (typeof value === 'string' && /^\d+$/.test(value)) value = Number(value);
  return typeof value === 'number' ? value : undefined;
}

if (ports.size) {
  const listen = net.Server.prototype.listen;
  net.Server.prototype.listen = function (...args) {
    const port = portOf(args[0]);
    if (port !== undefined && ports.has(port)) {
      note('listen', port);
      const error = Object.assign(new Error(`listen EADDRINUSE: address already in use :::${port} (refused by the quality phase)`),
        { code: 'EADDRINUSE', errno: -48, syscall: 'listen', port });
      process.nextTick(() => this.emit('error', error));
      return this;
    }
    return listen.apply(this, args);
  };

  const connect = net.Socket.prototype.connect;
  net.Socket.prototype.connect = function (...args) {
    // net.connect hands over its normalised arguments as an array whose first element is the options object
    const first = Array.isArray(args[0]) ? args[0][0] : args[0];
    const port = portOf(first);
    if (port !== undefined && ports.has(port)) {
      note('connect', port);
      const error = Object.assign(new Error(`connect ECONNREFUSED 127.0.0.1:${port} (refused by the quality phase)`),
        { code: 'ECONNREFUSED', errno: -61, syscall: 'connect', port });
      process.nextTick(() => this.destroy(error));
      return this;
    }
    return connect.apply(this, args);
  };
}
