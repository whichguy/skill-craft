/* Authored calibration server, never supplied to the subject. */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const config = {fault:process.env.ROUNDTABLE_FAULT || '', variant:process.env.ROUNDTABLE_VARIANT || 'standard',
  alternate:['alternate','all-collapsed','modal-drawer'].includes(process.env.ROUNDTABLE_VARIANT)};
const html = fs.readFileSync(path.join(__dirname,'reference.html'),'utf8').replace('/*CONFIG*/{}',JSON.stringify(config));
http.createServer((request,response) => {
  if (request.method === 'GET') { response.writeHead(200,{'content-type':'text/html'}); return response.end(html); }
  if (request.method === 'POST' && request.url === '/api/agent') {
    let body = '';
    request.on('data',chunk => { body += chunk; });
    request.on('end',() => {
      let text;
      try { text = JSON.parse(body).text; } catch {}
      response.setHeader('content-type','application/json');
      if (typeof text !== 'string' || !text.trim()) { response.writeHead(400); return response.end(JSON.stringify({error:'text required'})); }
      const plan = config.fault==='incomplete-plan' ? 'Next steps\n- Confirm scope\n- Review delivery' :
        'Next steps\n- Confirm scope\n- Assign an owner\n- Review delivery';
      response.end(JSON.stringify({text:text.startsWith('@Scribe plan') ? plan : 'Demo reply: ' + text}));
    });
    return;
  }
  response.writeHead(404); response.end();
}).listen(Number(process.env.PORT || 3000),'127.0.0.1',function () { console.log('ready ' + this.address().port); });
