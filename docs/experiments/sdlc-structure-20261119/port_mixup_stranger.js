'use strict';

/**
 * "Another program" for port_mixup_outcomes.py: it listens on 127.0.0.1 at the given port and treats every caller one way.
 *
 *   node port_mixup_stranger.js PORT drops|json|text|silent
 *
 * drops: hangs up at once.  json: answers 200 with JSON of its own.  text: answers 404 in plain text.
 * silent: takes the call and never answers.  It prints "listening" when it is ready.
 */

const http = require('node:http');
const net = require('node:net');

const port = Number(process.argv[2]);
const behaviour = process.argv[3];

const answers = {
  json: (res) => {
    res.setHeader('content-type', 'application/json');
    res.end(JSON.stringify({ game: 'g' }));
  },
  text: (res) => {
    res.statusCode = 404;
    res.setHeader('content-type', 'text/plain');
    res.end('Not Found');
  },
};

const server = behaviour === 'silent' ? net.createServer(() => {})
  : behaviour === 'drops' ? net.createServer((socket) => socket.destroy())
    : http.createServer((req, res) => answers[behaviour](res));
server.listen(port, '127.0.0.1', () => console.log('listening'));
