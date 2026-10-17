const http=require('node:http');
http.createServer((req,res)=>{
  if(req.url==='/'){res.writeHead(200,{'content-type':'text/html'});return res.end('<title>Battleship</title><h1>Battleship</h1>');}
  if(req.url==='/api/new'){res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({game:'g',gameOver:true}));}
  if(req.url==='/api/fire'){req.resume();res.writeHead(200,{'content-type':'application/json'});return res.end(JSON.stringify({result:'miss',gameOver:true,shots:1,hits:0}));}
  res.writeHead(404);res.end();
}).listen(Number(process.env.PORT||3000),'127.0.0.1');
