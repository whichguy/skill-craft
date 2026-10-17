require('http').createServer((req,res)=>{res.writeHead(200,{'content-type':'text/html'});res.end('<title>Battleship</title> stale sibling app')}).listen(Number(process.env.PORT));
