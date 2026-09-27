#!/usr/bin/env node
// A program that starts like the real one and does nothing. Given a port, it
// listens and answers 404 to everything (a server); otherwise it exits 0 with
// no output (a command line). An oracle check that passes against it tests
// nothing (admission gate, S-9).
import http from 'node:http'

const args = process.argv.slice(2)
const at = args.findIndex((a) => a === '--port' || a === '-p')
if (at < 0 && !process.env.PORT) process.exit(0)
const port = Number(at >= 0 ? args[at + 1] : process.env.PORT)
http.createServer((req, res) => {
  res.statusCode = 404
  res.end()
}).listen(port, () => console.log(`listening on ${port}`))
