import assert from 'node:assert/strict'
import test from 'node:test'

import { asJson, http, withServer } from './harness.mjs'

function posts(items) {
  return { posts: items }
}

function expectIds(body, ids) {
  assert.ok(Array.isArray(body), `expected a list, got ${JSON.stringify(body)}`)
  assert.deepEqual(
    body.map((item) => item.id),
    ids,
  )
}

const cases = [
  {
    query: 'views:gt=100&title:eq=a',
    db: posts([
      { id: '1', views: 150, title: 'a' },
      { id: '2', views: 150, title: 'b' },
      { id: '3', views: 50, title: 'a' },
    ]),
    ids: ['1'],
  },
  {
    query: 'title=hello',
    db: posts([
      { id: '1', title: 'hello' },
      { id: '2', title: 'Hello' },
      { id: '3', title: 'hell' },
    ]),
    ids: ['1'],
  },
  {
    query: 'author.name:lt=c&author.id:ne=2',
    db: posts([
      { id: '1', author: { name: 'b', id: 1 } },
      { id: '2', author: { name: 'b', id: 2 } },
      { id: '3', author: { name: 'd', id: 1 } },
      { id: '4', author: { name: 'a', id: 3 } },
    ]),
    ids: ['1', '4'],
  },
  {
    query: 'views:gt=100&views:lt=300',
    db: posts([
      { id: '1', views: 150 },
      { id: '2', views: 100 },
      { id: '3', views: 300 },
      { id: '4', views: 200 },
      { id: '5', views: 99 },
    ]),
    ids: ['1', '4'],
  },
  {
    query: 'name:eq=Alice',
    db: posts([
      { id: '1', name: 'Alice' },
      { id: '2', name: 'alice' },
      { id: '3', name: 'Bob' },
    ]),
    ids: ['1'],
  },
  {
    query: 'views:gt=100&published:eq=true&ratio:lt=0.5&deleted:eq=null',
    db: posts([
      { id: '1', views: 150, published: true, ratio: 0.4, deleted: null },
      { id: '2', views: 100, published: true, ratio: 0.4, deleted: null },
      { id: '3', views: 150, published: false, ratio: 0.4, deleted: null },
      { id: '4', views: 150, published: true, ratio: 0.5, deleted: null },
      { id: '5', views: 150, published: true, ratio: 0.4, deleted: 'x' },
      { id: '6', views: 150, published: true, ratio: 0.4 },
      { id: '7', views: 150, published: 'true', ratio: 0.4, deleted: null },
    ]),
    ids: ['1'],
  },
  {
    query: 'views:foo=100&title:eq=a',
    db: posts([
      { id: '1', title: 'a', views: 1 },
      { id: '2', title: 'a', views: 100 },
      { id: '3', title: 'b', views: 100 },
    ]),
    ids: ['1', '2'],
  },
  {
    query: 'views:foo=100',
    db: posts([
      { id: '1', views: 100 },
      { id: '2', views: 5 },
    ]),
    ids: ['1', '2'],
  },
  {
    query: 'views_gt=100&title_eq=a',
    db: posts([
      { id: '1', views: 150, title: 'a' },
      { id: '2', views: 150, title: 'b' },
      { id: '3', views: 50, title: 'a' },
    ]),
    ids: ['1'],
  },
  {
    query: 'first_name_eq=Alice&author.first_name_ne=Bob',
    db: posts([
      { id: '1', first_name: 'Alice', author: { first_name: 'Ann' } },
      { id: '2', first_name: 'Alice', author: { first_name: 'Bob' } },
      { id: '3', first_name: 'Alicia', author: { first_name: 'Ann' } },
      { id: '4', first_name: 'Bob', author: { first_name: 'Ann' } },
    ]),
    ids: ['1'],
  },
  {
    query: 'first_name=Alice',
    db: posts([
      { id: '1', first_name: 'Alice' },
      { id: '2', first_name: 'Bob' },
      { id: '3', first: { name: 'Alice' } },
    ]),
    ids: ['1'],
  },
  {
    query: 'views_gt=100&views:lt=300',
    db: posts([
      { id: '1', views: 150 },
      { id: '2', views: 100 },
      { id: '3', views: 300 },
      { id: '4', views: 200 },
    ]),
    ids: ['1', '4'],
  },
  {
    // Collection ids are strings, while this list is parsed as numbers,
    // so strict equality matches nothing.
    query: 'id:in=1,3',
    db: posts([{ id: 1 }, { id: 2 }, { id: 3 }]),
    ids: [],
  },
  {
    query: 'title_in=hello,world',
    db: posts([
      { id: '1', title: 'hello' },
      { id: '2', title: 'world' },
      { id: '3', title: 'Hello' },
      { id: '4', title: 'hell' },
    ]),
    ids: ['1', '2'],
  },
  {
    query: 'title:contains=ello',
    db: posts([
      { id: '1', title: 'Hello' },
      { id: '2', title: 'ELLO' },
      { id: '3', title: 'world' },
      { id: '4', title: 'hello world' },
    ]),
    ids: ['1', '2', '4'],
  },
  {
    query: 'title:startsWith=hel',
    db: posts([
      { id: '1', title: 'Hello' },
      { id: '2', title: 'HELium' },
      { id: '3', title: 'shell' },
      { id: '4', title: 'hel' },
    ]),
    ids: ['1', '2', '4'],
  },
  {
    query: 'title:endsWith=rld',
    db: posts([
      { id: '1', title: 'World' },
      { id: '2', title: 'world' },
      { id: '3', title: 'old' },
      { id: '4', title: 'rld' },
    ]),
    ids: ['1', '2', '4'],
  },
]

test('parseWhere', { timeout: 180_000 }, async (t) => {
  for (const tc of cases) {
    await t.test(tc.query, { timeout: 20_000 }, async () => {
      await withServer(tc.db, async ({ baseUrl }) => {
        const result = await http(baseUrl, `/posts?${tc.query}`)
        assert.equal(result.status, 200, result.text)
        expectIds(asJson(result), tc.ids)
      })
    })
  }
})
