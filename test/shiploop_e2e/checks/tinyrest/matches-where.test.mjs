import assert from 'node:assert/strict'
import test from 'node:test'

import { asJson, http, withServer } from './harness.mjs'

const record = { id: '1', a: 10, b: 20, c: 'x', nested: { a: 10, b: 20 } }

const cases = [
  [{ a: { eq: 10 } }, true],
  [{ a: { eq: 11 } }, false],
  [{ c: { ne: 'y' } }, true],
  [{ c: { ne: 'x' } }, false],
  [{ a: { lt: 11 } }, true],
  [{ a: { lt: 10 } }, false],
  [{ a: { lte: 10 } }, true],
  [{ a: { lte: 9 } }, false],
  [{ b: { gt: 19 } }, true],
  [{ b: { gt: 20 } }, false],
  [{ b: { gte: 20 } }, true],
  [{ b: { gte: 21 } }, false],
  [{ a: { gt: 0 }, b: { lt: 30 } }, true],
  [{ a: { gt: 10 }, b: { lt: 30 } }, false],
  [{ or: [{ a: { lt: 0 } }, { b: { gt: 19 } }] }, true],
  [{ or: [{ a: { lt: 0 } }, { b: { gt: 20 } }] }, false],
  [{ nested: { a: { eq: 10 } } }, true],
  [{ nested: { b: { lt: 20 } } }, false],
  [{ a: { in: [10, 11] } }, true],
  [{ a: { in: [1, 2] } }, false],
  [{ c: { in: ['x', 'y'] } }, true],
  [{ c: { in: ['y', 'z'] } }, false],
  [{ a: { in: [10, 11], gt: 9 } }, true],
  [{ a: { in: [10, 11], gt: 10 } }, false],
  [{ a: { foo: 10 } }, true],
  [{ a: { foo: 10, eq: 10 } }, true],
  [{ missing: { foo: 1 } }, true],
  [{ c: { contains: 'x' } }, true],
  [{ c: { contains: 'X' } }, true],
  [{ c: { contains: 'z' } }, false],
  [{ a: { contains: '1' } }, false],
  [{ c: { contains: 1 } }, false],
  [{ c: { startsWith: 'x' } }, true],
  [{ c: { startsWith: 'X' } }, true],
  [{ c: { startsWith: 'z' } }, false],
  [{ a: { startsWith: '1' } }, false],
  [{ c: { startsWith: 1 } }, false],
  [{ c: { endsWith: 'x' } }, true],
  [{ c: { endsWith: 'X' } }, true],
  [{ c: { endsWith: 'z' } }, false],
  [{ a: { endsWith: '1' } }, false],
  [{ c: { endsWith: 1 } }, false],
]

test('matchesWhere', { timeout: 180_000 }, async (t) => {
  for (const [query, expected] of cases) {
    await t.test(JSON.stringify(query), { timeout: 20_000 }, async () => {
      await withServer({ items: [record] }, async ({ baseUrl }) => {
        const where = encodeURIComponent(JSON.stringify(query))
        const result = await http(baseUrl, `/items?_where=${where}`)
        assert.equal(result.status, 200, result.text)
        const body = asJson(result)
        assert.deepEqual(body, expected ? [record] : [])
      })
    })
  }
})
