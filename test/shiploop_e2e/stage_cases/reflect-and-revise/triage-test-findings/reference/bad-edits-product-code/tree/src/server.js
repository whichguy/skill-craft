'use strict';

// Improperly edited during reflect-and-revise
const http = require('node:http');
module.exports = { createServer: () => http.createServer() };
