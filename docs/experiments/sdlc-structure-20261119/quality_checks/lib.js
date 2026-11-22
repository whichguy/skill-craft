'use strict';
const { spawn } = require('node:child_process');
const http = require('node:http');
const net = require('node:net');

function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.on('error', reject);
    s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => resolve(port)); });
  });
}
function canConnect(port) {
  return new Promise((resolve) => {
    const c = net.connect(port, '127.0.0.1');
    c.on('connect', () => { c.destroy(); resolve(true); });
    c.on('error', () => resolve(false));
  });
}
async function start(dir, entry, env) {
  const port = await freePort();
  const child = spawn(process.execPath, [entry], { cwd: dir, env: { PATH: process.env.PATH, HOME: process.env.HOME, PORT: String(port), ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = ''; let exited = null;
  child.stdout.on('data', (d) => { out += d; }); child.stderr.on('data', (d) => { out += d; });
  child.on('exit', (code, sig) => { exited = { code, sig }; });
  for (let i = 0; i < 100; i += 1) {
    if (exited) break;
    if (await canConnect(port)) return { port, child, started: true, out: () => out, stop: () => stop(child) };
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!exited) child.kill('SIGKILL');
  return { started: false, exited, out: () => out, stop: async () => {} };
}
function stop(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.signalCode) return resolve();
    child.on('exit', () => resolve());
    child.kill('SIGTERM');
    setTimeout(() => child.kill('SIGKILL'), 3000).unref();
  });
}
function req(port, method, path, body) {
  return new Promise((resolve) => {
    const data = body === undefined ? null : JSON.stringify(body);
    const r = http.request({ host: '127.0.0.1', port, method, path, headers: data ? { 'content-type': 'application/json', 'content-length': Buffer.byteLength(data) } : {} }, (res) => {
      let text = ''; res.on('data', (d) => { text += d; });
      res.on('end', () => { let json; try { json = JSON.parse(text); } catch { json = text; } resolve({ status: res.statusCode, body: json }); });
    });
    r.on('error', (e) => resolve({ status: 0, body: String(e) }));
    if (data) r.write(data);
    r.end();
  });
}
module.exports = { start, req };
