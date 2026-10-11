'use strict';

const http = require('node:http');
const { getUser, listUsers } = require('./users');

function send(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
}

/** An HTTP server for the user store; not listening until the caller calls listen(). */
function createServer() {
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());
    const match = /^\/users\/(\d+)$/.exec(url.pathname);
    if (req.method === 'GET' && match) {
      const user = getUser(Number(match[1]));
      return user ? send(res, 200, user) : send(res, 404, { error: 'not found' });
    }
    return send(res, 404, { error: 'not found' });
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  createServer().listen(port, () => console.log(`listening on ${port}`));
}

module.exports = { createServer };
