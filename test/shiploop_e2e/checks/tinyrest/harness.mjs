import { spawn } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { once } from 'node:events'
import fs from 'node:fs'
import net from 'node:net'
import os from 'node:os'
import path from 'node:path'

const children = new Set()

process.on('exit', () => {
  for (const pid of children) {
    try {
      process.kill(-pid, 'SIGKILL')
    } catch {
      // already gone
    }
  }
})

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function shQuote(value) {
  return `'${String(value).replaceAll("'", `'\\''`)}'`
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : 0
      server.close(() => resolve(port))
    })
  })
}

class StartupError extends Error {}

async function stopChild(child) {
  const pid = child.pid
  if (!pid) return
  children.delete(pid)
  if (child.exitCode !== null || child.signalCode !== null) return
  try {
    process.kill(-pid, 'SIGTERM')
  } catch {
    try {
      child.kill('SIGTERM')
    } catch {
      return
    }
  }
  const exited = await Promise.race([
    once(child, 'exit').then(() => 'exit'),
    delay(1500).then(() => 'timeout'),
  ])
  if (exited === 'timeout') {
    try {
      process.kill(-pid, 'SIGKILL')
    } catch {
      // already gone
    }
    await Promise.race([once(child, 'exit'), delay(1000)])
  }
}

/**
 * Start one server from APP_CMD against a temp database.
 * `data` is the JSON document clients edit; a private readiness record is added
 * so a port collision cannot be mistaken for this process.
 */
export async function withServer(data, fn, options = {}) {
  const appCmd = process.env.APP_CMD
  if (!appCmd) {
    throw new Error('APP_CMD is not set')
  }

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'oracle-'))
  const file = path.join(dir, 'db.json')
  const token = randomBytes(8).toString('hex')
  const db = { ...data, oracleReady: { token } }
  fs.writeFileSync(file, JSON.stringify(db, null, 2))

  const publicDir = path.join(dir, 'public')
  fs.mkdirSync(publicDir)
  fs.writeFileSync(
    path.join(publicDir, 'test.html'),
    options.publicBody ?? 'public-file',
  )

  const staticDir = path.join(dir, 'static')
  fs.mkdirSync(staticDir)
  fs.writeFileSync(path.join(staticDir, 'file.html'), options.staticBody ?? 'utf-8')

  const staticDirs = options.staticDirs ?? [staticDir]
  let lastError = new Error('server did not start')

  try {
    for (let attempt = 0; attempt < 8; attempt++) {
      const port = await freePort()
      const args = ['-p', String(port), '-h', '127.0.0.1']
      for (const staticPath of staticDirs) {
        args.push('-s', staticPath)
      }
      args.push(file)
      const command = `${appCmd} ${args.map(shQuote).join(' ')}`
      const child = spawn('/bin/sh', ['-c', command], {
        cwd: dir,
        detached: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      })
      if (child.pid) children.add(child.pid)
      let logs = ''
      const capture = (chunk) => {
        logs += chunk.toString()
        if (logs.length > 12_000) logs = logs.slice(-12_000)
      }
      child.stdout?.on('data', capture)
      child.stderr?.on('data', capture)
      child.on('error', (error) => {
        logs += `\n${error.message}`
      })

      const baseUrl = `http://127.0.0.1:${port}`
      try {
        await waitUntilReady(baseUrl, token, child)
        try {
          return await fn({ baseUrl, dir, file, port })
        } finally {
          await stopChild(child)
        }
      } catch (error) {
        await stopChild(child)
        if (error instanceof StartupError) {
          lastError = new StartupError(`${error.message}\n${logs}`)
          continue
        }
        throw error
      }
    }
    throw lastError
  } finally {
    fs.rmSync(dir, { recursive: true, force: true })
  }
}

async function waitUntilReady(baseUrl, token, child) {
  const started = Date.now()
  while (Date.now() - started < 10_000) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new StartupError(
        `server exited before it answered (code ${child.exitCode}, signal ${child.signalCode})`,
      )
    }
    try {
      const response = await fetch(`${baseUrl}/oracleReady`, {
        signal: AbortSignal.timeout(500),
      })
      const text = await response.text()
      if (response.status === 200) {
        const body = JSON.parse(text)
        if (body?.token === token) return
      }
    } catch {
      // not listening yet, or this port belongs to someone else
    }
    await delay(40)
  }
  throw new StartupError('server did not answer within 10 seconds')
}

export async function http(baseUrl, urlPath, init) {
  const response = await fetch(`${baseUrl}${urlPath}`, init)
  const text = await response.text()
  return { status: response.status, text, response }
}

export function asJson(result) {
  try {
    return JSON.parse(result.text)
  } catch {
    throw new Error(
      `expected JSON, got HTTP ${result.status}: ${result.text.slice(0, 500)}`,
    )
  }
}

export function sendJson(method, body) {
  return {
    method,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  }
}
