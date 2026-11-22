'use strict';

/**
 * A preload for port_mixup_suite_probe.py: one line per server that starts listening, "family address port", appended to the file
 * named by LISTEN_LOG. It changes nothing a test can see.
 *
 *   NODE_OPTIONS="--require /path/to/port_mixup_count_listens.js" LISTEN_LOG=/path/to/log node --test
 */

const fs = require('node:fs');
const net = require('node:net');

const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function counted(...args) {
  this.once('listening', () => {
    const address = this.address();
    if (address && typeof address === 'object') {
      fs.appendFileSync(process.env.LISTEN_LOG, `${address.family} ${address.address} ${address.port}\n`);
    }
  });
  return listen.apply(this, args);
};
