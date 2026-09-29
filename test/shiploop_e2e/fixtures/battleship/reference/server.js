const http = require('node:http');
const { randomUUID } = require('node:crypto');
const { createGame, fire } = require('./rules');

const games = new Map();
const page = `<!doctype html><html><head><meta charset="utf-8"><title>Battleship</title>
<style>body{font:16px sans-serif}#board{display:grid;grid-template-columns:repeat(10,2.4rem);gap:3px}.cell{height:2.4rem}.miss{background:#ddd}.hit{background:#e88}</style></head><body>
<h1>Battleship</h1><p>Shots: <span id="shots">0</span> Hits: <span id="hits">0</span> Accuracy: <span id="accuracy">0%</span></p>
<p id="sunk"></p><div id="board"></div><script>
(async()=>{const game=(await fetch('/api/new').then(r=>r.json())).game;const board=document.querySelector('#board');
for(let row=0;row<10;row++)for(let col=0;col<10;col++){const cell=document.createElement('button');cell.className='cell';cell.textContent=` + "`${row + 1},${col + 1}`" + `;cell.addEventListener('click',async()=>{if(cell.disabled)return;cell.disabled=true;
const result=await fetch('/api/fire',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({game,row,col})}).then(r=>r.json());
document.querySelector('#shots').textContent=result.shots;document.querySelector('#hits').textContent=result.hits;
document.querySelector('#accuracy').textContent=(100*result.hits/result.shots).toFixed(0)+'%';cell.classList.add(result.result);
if(result.result==='sunk')document.querySelector('#sunk').textContent='Sunk '+result.ship;if(result.gameOver)board.querySelectorAll('button').forEach(b=>b.disabled=true);});board.append(cell);}})();
</script></body></html>`;

function send(response, status, body, type = 'application/json') {
  response.writeHead(status, { 'content-type': `${type}; charset=utf-8` });
  response.end(type === 'application/json' ? JSON.stringify(body) : body);
}

const server = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://localhost');
  if (request.method === 'GET' && url.pathname === '/') return send(response, 200, page, 'text/html');
  if (request.method === 'GET' && url.pathname === '/api/new') {
    const id = randomUUID();
    games.set(id, createGame(id));
    return send(response, 200, { game: id });
  }
  if (request.method === 'POST' && url.pathname === '/api/fire') {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => { body += chunk; });
    request.on('end', () => {
      try {
        const input = JSON.parse(body);
        const game = games.get(input.game);
        if (!game) return send(response, 404, { error: 'unknown game' });
        return send(response, 200, fire(game, input.row, input.col));
      } catch {
        return send(response, 400, { error: 'invalid request' });
      }
    });
    return;
  }
  return send(response, 404, { error: 'not found' });
});

server.listen(Number(process.env.PORT || 3000), '127.0.0.1');
