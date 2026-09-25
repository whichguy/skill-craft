'use strict';

// Deterministic external-launch fixture. This never launches a model or agent.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

function read(dir) {
  const fixturePath = path.join(dir, 'fake-host.json');
  return fs.existsSync(fixturePath) ? JSON.parse(fs.readFileSync(fixturePath)) : [];
}

function launch(dir, key) {
  const tasks = read(dir);
  const task = { key, handle: 'fixture-' + crypto.randomUUID() };
  tasks.push(task);
  fs.writeFileSync(path.join(dir, 'fake-host.json'), JSON.stringify(tasks));
  return task;
}

function lookup(dir, key) {
  return read(dir).filter((task) => task.key === key);
}

module.exports = { read, launch, lookup };
