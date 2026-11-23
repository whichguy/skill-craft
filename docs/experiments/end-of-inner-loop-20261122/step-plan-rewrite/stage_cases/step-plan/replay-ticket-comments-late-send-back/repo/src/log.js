'use strict';

/**
 * A small logger: one line per message on standard error, `<time> <level> <message>`. The silent logger drops
 * everything; tests use it.
 */
function createLogger({ stream = process.stderr, clock = { now: () => new Date() }, silent = false } = {}) {
  const write = (level, message) => {
    if (!silent) stream.write(`${clock.now().toISOString()} ${level} ${message}\n`);
  };
  return {
    info: (message) => write('info', message),
    warn: (message) => write('warn', message),
    error: (message, error) => write('error', error ? `${message}: ${error.stack || error}` : message),
    request: (req, status, ms) => write('info', `${req.method} ${req.url} ${status} ${ms.toFixed(1)}ms`),
  };
}

const silentLogger = createLogger({ silent: true });

module.exports = { createLogger, silentLogger };
