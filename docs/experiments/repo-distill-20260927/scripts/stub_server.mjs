#!/usr/bin/env node
// A program that starts like the real one and does nothing: it listens on the
// requested port and answers 404 to everything. An oracle test that passes
// against it tests nothing (admission gate, S-9).
import http from 'node:http'

const args = process.argv.slice(2)
const at = args.findIndex((a) => a === '--port' || a === '-p')
const port = Number(at >= 0 ? args[at + 1] : process.env.PORT || 3000)
http.createServer((req, res) => {
  res.statusCode = 404
  res.end()
}).listen(port, () => console.log(`listening on ${port}`))
