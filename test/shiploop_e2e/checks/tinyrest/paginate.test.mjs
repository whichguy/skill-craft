import assert from 'node:assert/strict'
import test from 'node:test'

import { asJson, http, withServer } from './harness.mjs'

function records(values) {
  return values.map((n) => ({ id: String(n), n }))
}

const cases = [
  {
    name: 'page=1 perPage=2 items=5 -> [1,2]',
    values: [1, 2, 3, 4, 5],
    page: 1,
    perPage: 2,
    expected: {
      first: 1,
      prev: null,
      next: 2,
      last: 3,
      pages: 3,
      items: 5,
      data: [1, 2],
    },
  },
  {
    name: 'page=2 perPage=2 items=5 -> [3,4]',
    values: [1, 2, 3, 4, 5],
    page: 2,
    perPage: 2,
    expected: {
      first: 1,
      prev: 1,
      next: 3,
      last: 3,
      pages: 3,
      items: 5,
      data: [3, 4],
    },
  },
  {
    name: 'page=9 perPage=2 items=5 -> clamp to last',
    values: [1, 2, 3, 4, 5],
    page: 9,
    perPage: 2,
    expected: {
      first: 1,
      prev: 2,
      next: null,
      last: 3,
      pages: 3,
      items: 5,
      data: [5],
    },
  },
  {
    name: 'page=0 perPage=2 items=3 -> clamp to first',
    values: [1, 2, 3],
    page: 0,
    perPage: 2,
    expected: {
      first: 1,
      prev: null,
      next: 2,
      last: 2,
      pages: 2,
      items: 3,
      data: [1, 2],
    },
  },
  {
    name: 'items=[] page=1 perPage=2 -> stable empty pagination',
    values: [],
    page: 1,
    perPage: 2,
    expected: {
      first: 1,
      prev: null,
      next: null,
      last: 1,
      pages: 1,
      items: 0,
      data: [],
    },
  },
  {
    name: 'perPage=0 -> clamp perPage to 1',
    values: [1, 2, 3],
    page: 1,
    perPage: 0,
    expected: {
      first: 1,
      prev: null,
      next: 2,
      last: 3,
      pages: 3,
      items: 3,
      data: [1],
    },
  },
]

test('paginate', { timeout: 120_000 }, async (t) => {
  for (const tc of cases) {
    await t.test(tc.name, { timeout: 20_000 }, async () => {
      const posts = records(tc.values)
      await withServer({ posts }, async ({ baseUrl }) => {
        const result = await http(
          baseUrl,
          `/posts?_page=${tc.page}&_per_page=${tc.perPage}`,
        )
        assert.equal(result.status, 200)
        const body = asJson(result)
        assert.deepEqual(
          {
            first: body.first,
            prev: body.prev,
            next: body.next,
            last: body.last,
            pages: body.pages,
            items: body.items,
            data: body.data.map((item) => item.n),
          },
          tc.expected,
        )
      })
    })
  }
})
