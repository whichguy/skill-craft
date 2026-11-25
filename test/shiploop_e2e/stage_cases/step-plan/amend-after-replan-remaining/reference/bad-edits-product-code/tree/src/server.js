'use strict';

// Improperly edited during step-plan
const http = require('node:http');
module.exports = { createServer: () => http.createServer() };
