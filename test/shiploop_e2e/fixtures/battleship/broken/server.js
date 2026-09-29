const http = require('node:http');
const page = '<!doctype html><html><head><title>Battleship</title></head><body><h1>Battleship</h1></body></html>';

const server = http.createServer((request, response) => {
  const path = new URL(request.url, 'http://local').pathname;
  response.writeHead(200, { 'content-type': path === '/' ? 'text/html' : 'application/json' });
  if (path === '/') return response.end(page);
  if (path === '/api/new') return response.end(JSON.stringify({ game: 'stub' }));
  if (path === '/api/fire') {
    request.resume();
    return response.end(JSON.stringify({ result: 'miss', gameOver: true, shots: 1, hits: 0 }));
  }
  response.writeHead(404);
  response.end('{}');
});

server.listen(Number(process.env.PORT || 3000), '127.0.0.1');
