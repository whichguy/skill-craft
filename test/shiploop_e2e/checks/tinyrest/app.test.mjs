import assert from 'node:assert/strict'
import test from 'node:test'

import { asJson, http, sendJson, withServer } from './harness.mjs'

const data = {
  posts: [{ id: '1', title: 'foo' }],
  comments: [{ id: '1', postId: '1' }],
  object: { f1: 'foo' },
}

const routes = [
  ['GET', '/', 200],
  ['GET', '/test.html', 200],
  ['GET', '/file.html', 200],
  ['OPTIONS', '/posts', 204],
  ['GET', '/posts', 200],
  ['GET', '/posts?_embed=comments', 200],
  ['GET', '/posts/1', 200],
  ['GET', '/posts/-1', 404],
  ['GET', '/posts/1?_embed=comments', 200],
  ['GET', '/comments', 200],
  ['GET', '/comments?postId=1', 200],
  ['GET', '/object', 200],
  ['GET', '/object/1', 404],
  ['GET', '/not-found', 404],
  ['POST', '/posts', 201],
  ['POST', '/posts/1', 404],
  ['POST', '/posts/-1', 404],
  ['POST', '/object', 404],
  ['POST', '/object/1', 404],
  ['POST', '/not-found', 404],
  ['PUT', '/posts', 404],
  ['PUT', '/posts/1', 200],
  ['PUT', '/object', 200],
  ['PUT', '/object/1', 404],
  ['PUT', '/posts/-1', 404],
  ['PUT', '/not-found', 404],
  ['PATCH', '/posts', 404],
  ['PATCH', '/posts/1', 200],
  ['PATCH', '/object', 200],
  ['PATCH', '/object/1', 404],
  ['PATCH', '/posts/-1', 404],
  ['PATCH', '/not-found', 404],
  ['DELETE', '/posts', 404],
  ['DELETE', '/posts/1', 200],
  ['DELETE', '/object', 404],
  ['DELETE', '/object/1', 404],
  ['DELETE', '/posts/-1', 404],
  ['DELETE', '/not-found', 404],
]

test('createApp', { timeout: 180_000 }, async (t) => {
  for (const [method, url, statusCode] of routes) {
    await t.test(`${method} ${url}`, { timeout: 20_000 }, async () => {
      await withServer(data, async ({ baseUrl }) => {
        const result = await http(baseUrl, url, { method })
        assert.equal(result.status, statusCode, result.text)
        if (statusCode === 404) {
          assert.deepEqual(asJson(result), { error: 'Not Found' })
        }
        if (url === '/test.html') {
          assert.equal(result.text, 'public-file')
        }
        if (url === '/file.html') {
          assert.equal(result.text, 'utf-8')
        }
      })
    })
  }

  await t.test('GET /posts?_where=... uses JSON query', { timeout: 20_000 }, async () => {
    await withServer(data, async ({ baseUrl }) => {
      const where = encodeURIComponent(JSON.stringify({ title: { eq: 'foo' } }))
      const result = await http(baseUrl, `/posts?_where=${where}`)
      assert.equal(result.status, 200)
      assert.deepEqual(asJson(result), [{ id: '1', title: 'foo' }])
    })
  })

  await t.test(
    'GET /posts?_where=... overrides query params',
    { timeout: 20_000 },
    async () => {
      await withServer(data, async ({ baseUrl }) => {
        const where = encodeURIComponent(JSON.stringify({ title: { eq: 'foo' } }))
        const result = await http(baseUrl, `/posts?title:eq=bar&_where=${where}`)
        assert.equal(result.status, 200)
        assert.deepEqual(asJson(result), [{ id: '1', title: 'foo' }])
      })
    },
  )

  await t.test('POST /posts with array body returns 400', { timeout: 20_000 }, async () => {
    await withServer(data, async ({ baseUrl }) => {
      const result = await http(baseUrl, '/posts', sendJson('POST', [{ title: 'foo' }]))
      assert.equal(result.status, 400)
      assert.deepEqual(asJson(result), { error: 'Body must be a JSON object' })
    })
  })

  await t.test(
    'PATCH /posts/1 with string body returns 400',
    { timeout: 20_000 },
    async () => {
      await withServer(data, async ({ baseUrl }) => {
        const result = await http(baseUrl, '/posts/1', sendJson('PATCH', 'hello'))
        assert.equal(result.status, 400)
        assert.deepEqual(asJson(result), { error: 'Body must be a JSON object' })
      })
    },
  )

  await t.test('PUT /posts/1 with null body returns 400', { timeout: 20_000 }, async () => {
    await withServer(data, async ({ baseUrl }) => {
      const result = await http(baseUrl, '/posts/1', sendJson('PUT', null))
      assert.equal(result.status, 400)
      assert.deepEqual(asJson(result), { error: 'Body must be a JSON object' })
    })
  })
})
