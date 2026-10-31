'use strict';

const http = require('node:http');
const { createApp } = require('./app');
const { systemClock } = require('./clock');
const { ConfigError, loadConfig } = require('./config');
const { createLogger } = require('./log');
const { createNotifier } = require('./notifier');
const { DataFileError, createPersistence } = require('./persistence');
const { TicketStore } = require('./store');
const { Worker, deliverOutbox } = require('./worker');

/**
 * The service, put together from its settings (src/config.js): the store (with the data file when there is one), the
 * notifier, the worker and the HTTP server. Nothing listens or runs until start().
 */
function createService(config, { clock = systemClock, log = createLogger() } = {}) {
  const persistence = config.dataFile ? createPersistence(config.dataFile, { clock }) : null;
  const store = TicketStore.open({ clock, persistence });
  const notifier = createNotifier({ file: config.notifyFile, clock });
  const worker = new Worker({
    intervalMs: config.workerIntervalMs,
    jobs: [deliverOutbox({ store, notifier, log })],
    log,
  });
  const app = createApp({ store, maxBodyBytes: config.maxBodyBytes, log, logRequests: config.logRequests });
  const server = http.createServer(app);

  return {
    config,
    store,
    notifier,
    worker,
    server,

    /** Listen on config.port and start the worker. Resolves to the port listened on. */
    async start() {
      await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(config.port, () => {
          server.off('error', reject);
          resolve();
        });
      });
      worker.start();
      return server.address().port;
    },

    /** Stop the worker, let the requests in flight finish, stop listening and save. */
    async stop() {
      worker.stop();
      await new Promise((resolve) => {
        server.close(resolve);
        server.closeIdleConnections();
      });
      store.save();
    },
  };
}

async function main() {
  const log = createLogger();
  let service;
  try {
    service = createService(loadConfig(), { log });
  } catch (error) {
    if (error instanceof ConfigError || error instanceof DataFileError) {
      log.error(`cannot start: ${error.message}`);
      process.exit(2);
    }
    throw error;
  }
  const port = await service.start();
  const { dataFile, notifyFile, workerIntervalMs } = service.config;
  log.info(`tickets listening on ${port}; data ${dataFile || 'in memory'}; notifications ${notifyFile || 'in memory'}; ` +
    `worker ${workerIntervalMs ? `every ${workerIntervalMs} ms` : 'off'}`);
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.once(signal, () => {
      log.info(`${signal}: stopping`);
      service.stop().then(() => process.exit(0));
    });
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

module.exports = { createService };
