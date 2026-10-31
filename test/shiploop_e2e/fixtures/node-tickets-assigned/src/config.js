'use strict';

/**
 * The service's settings. Every one comes from an environment variable (README.md, "Configuration"); an unset or
 * empty variable takes its default.
 */

const DEFAULTS = Object.freeze({
  port: 4180,
  workerIntervalMs: 500,
  maxBodyBytes: 64 * 1024,
});

class ConfigError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ConfigError';
  }
}

/** A whole-number setting: `fallback` when unset or empty, else a whole number from `min` to `max`. */
function wholeNumber(env, name, fallback, { min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
  const text = (env[name] ?? '').trim();
  if (text === '') return fallback;
  if (!/^\d+$/.test(text)) throw new ConfigError(`${name} must be a whole number, not ${JSON.stringify(env[name])}`);
  const value = Number(text);
  if (value < min || value > max) throw new ConfigError(`${name} must be from ${min} to ${max}, not ${value}`);
  return value;
}

/** A file setting: the path as given, or null when unset or empty. */
function filePath(env, name) {
  const text = env[name] ?? '';
  return text.trim() === '' ? null : text;
}

/** The settings read from `env`. Throws ConfigError, naming the variable, for a value the service cannot use. */
function loadConfig(env = process.env) {
  return Object.freeze({
    port: wholeNumber(env, 'PORT', DEFAULTS.port, { max: 65535 }),
    dataFile: filePath(env, 'DATA_FILE'),
    notifyFile: filePath(env, 'NOTIFY_FILE'),
    workerIntervalMs: wholeNumber(env, 'WORKER_INTERVAL_MS', DEFAULTS.workerIntervalMs, { max: 60 * 60 * 1000 }),
    maxBodyBytes: wholeNumber(env, 'MAX_BODY_BYTES', DEFAULTS.maxBodyBytes, { min: 1024, max: 1024 * 1024 }),
    logRequests: env.LOG_REQUESTS === '1',
  });
}

module.exports = { ConfigError, DEFAULTS, loadConfig };
