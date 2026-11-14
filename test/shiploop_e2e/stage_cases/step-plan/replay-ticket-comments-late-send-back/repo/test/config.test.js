'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ConfigError, loadConfig } = require('../src/config');

const settings = ({ port, dataFile, notifyFile, workerIntervalMs, maxBodyBytes, logRequests }) =>
  ({ port, dataFile, notifyFile, workerIntervalMs, maxBodyBytes, logRequests });

test('every setting has a default', () => {
  assert.deepEqual(settings(loadConfig({})), {
    port: 4180,
    dataFile: null,
    notifyFile: null,
    workerIntervalMs: 500,
    maxBodyBytes: 65536,
    logRequests: false,
  });
});

test('reads each setting from its variable, and an empty one is unset', () => {
  const config = loadConfig({
    PORT: '8080',
    DATA_FILE: 'data/tickets.json',
    NOTIFY_FILE: '',
    WORKER_INTERVAL_MS: '0',
    MAX_BODY_BYTES: '2048',
    LOG_REQUESTS: '1',
  });
  assert.deepEqual(settings(config), {
    port: 8080,
    dataFile: 'data/tickets.json',
    notifyFile: null,
    workerIntervalMs: 0,
    maxBodyBytes: 2048,
    logRequests: true,
  });
});

test('a value the service cannot use names its variable', () => {
  for (const [env, message] of [
    [{ PORT: 'http' }, /PORT must be a whole number/],
    [{ PORT: '70000' }, /PORT must be from 0 to 65535/],
    [{ WORKER_INTERVAL_MS: '-5' }, /WORKER_INTERVAL_MS must be a whole number/],
    [{ MAX_BODY_BYTES: '10' }, /MAX_BODY_BYTES must be from 1024/],
  ]) {
    assert.throws(() => loadConfig(env), (error) => error instanceof ConfigError && message.test(error.message));
  }
});
