const http = require('node:http');
const { randomUUID } = require('node:crypto');
const { start, shoot } = require('./game-state');

const sessions = Object.create(null);
const page = `<!doctype html><html><head><title>Battleship</title><meta charset="utf-8"></head><body>
<h1>Battleship</h1><p id="shots">Shots: 0</p><p id="hits">Hits: 0</p><p id="accuracy">Accuracy: 0%</p><p id="message"></p><canvas id="battlefield" width="400" height="400" aria-label="10 by 10 Battleship grid"></canvas>
<script>
(async()=>{const id=(await fetch('/api/new').then(r=>r.json())).game;const canvas=document.querySelector('#battlefield');const ctx=canvas.getContext('2d');const fired=new Set();const cell=40;
function draw(){ctx.clearRect(0,0,400,400);ctx.strokeStyle='#426';for(let n=0;n<=10;n++){ctx.beginPath();ctx.moveTo(n*cell,0);ctx.lineTo(n*cell,400);ctx.moveTo(0,n*cell);ctx.lineTo(400,n*cell);ctx.stroke();}}
draw();canvas.addEventListener('click',async event=>{const rect=canvas.getBoundingClientRect();const col=Math.floor((event.clientX-rect.left)*400/rect.width/cell);const row=Math.floor((event.clientY-rect.top)*400/rect.height/cell);const key=row+','+col;if(fired.has(key))return;fired.add(key);
const shot=await fetch('/api/fire',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({game:id,row:row+1,col:col+1})}).then(r=>r.json());document.querySelector('#shots').textContent='Shots: '+shot.shots;document.querySelector('#hits').textContent='Hits: '+shot.hits;document.querySelector('#accuracy').textContent='Accuracy: '+(100*shot.hits/shot.shots).toFixed(0)+'%';
ctx.fillStyle=shot.result==='miss'?'#aaa':'#d43';ctx.beginPath();ctx.arc(col*cell+cell/2,row*cell+cell/2,8,0,Math.PI*2);ctx.fill();if(shot.result==='sunk')document.querySelector('#message').textContent='Sunk '+shot.ship;});})();
</script></body></html>`;

function json(response, status, value) {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(value));
}

const server = http.createServer((request, response) => {
  const path = new URL(request.url, 'http://local').pathname;
  if (request.method === 'GET' && path === '/') {
    response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    return response.end(page);
  }
  if (request.method === 'GET' && path === '/api/new') {
    const id = randomUUID();
    sessions[id] = start();
    return json(response, 200, { id });
  }
  if (request.method === 'POST' && path === '/api/fire') {
    let text = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => { text += chunk; });
    request.on('end', () => {
      try {
        const input = JSON.parse(text);
        const state = sessions[input.game];
        if (!state) return json(response, 404, { error: 'unknown game' });
        return json(response, 200, shoot(state, input.row, input.col));
      } catch {
        return json(response, 400, { error: 'invalid request' });
      }
    });
    return;
  }
  return json(response, 404, { error: 'not found' });
});

server.listen(Number(process.env.PORT || 3000), '127.0.0.1');
