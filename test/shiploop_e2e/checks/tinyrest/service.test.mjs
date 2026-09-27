import assert from 'node:assert/strict'
import test from 'node:test'

import { asJson, http, sendJson, withServer } from './harness.mjs'

const post1 = {
  id: '1',
  title: 'a',
  views: 100,
  published: true,
  author: { name: 'foo' },
  tags: ['foo', 'bar'],
}
const post2 = {
  id: '2',
  title: 'b',
  views: 200,
  published: false,
  author: { name: 'bar' },
  tags: ['bar'],
}
const post3 = {
  id: '3',
  title: 'c',
  views: 300,
  published: false,
  author: { name: 'baz' },
  tags: ['foo'],
}
const comment1 = { id: '1', title: 'a', postId: '1' }
const obj = { f1: 'foo' }

function data() {
  return {
    posts: [post1, post2, post3],
    comments: [comment1],
    object: obj,
  }
}

async function bodyOf(baseUrl, urlPath, init) {
  const result = await http(baseUrl, urlPath, init)
  return { status: result.status, body: asJson(result), text: result.text }
}

test('findById', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const found = await bodyOf(baseUrl, '/posts/1')
    assert.equal(found.status, 200)
    assert.deepEqual(found.body, post1)

    const missing = await bodyOf(baseUrl, '/posts/xxx')
    assert.equal(missing.status, 404)
    assert.deepEqual(missing.body, { error: 'Not Found' })

    const withComments = await bodyOf(baseUrl, '/posts/1?_embed=comments')
    assert.equal(withComments.status, 200)
    assert.deepEqual(withComments.body, { ...post1, comments: [comment1] })

    const withPost = await bodyOf(baseUrl, '/comments/1?_embed=post')
    assert.equal(withPost.status, 200)
    assert.deepEqual(withPost.body, { ...comment1, post: post1 })

    const unknown = await bodyOf(baseUrl, '/xxx/1')
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })
  })
})

test('find', { timeout: 120_000 }, async (t) => {
  await t.test('{"where":{"title":{"eq":"b"}}}', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const where = encodeURIComponent(JSON.stringify({ title: { eq: 'b' } }))
      const result = await bodyOf(baseUrl, `/posts?_where=${where}`)
      assert.equal(result.status, 200)
      assert.deepEqual(result.body, [post2])
    })
  })

  await t.test(
    '{"where":{"author":{"name":{"eq":"bar"}}}}',
    { timeout: 20_000 },
    async () => {
      await withServer(data(), async ({ baseUrl }) => {
        const where = encodeURIComponent(
          JSON.stringify({ author: { name: { eq: 'bar' } } }),
        )
        const result = await bodyOf(baseUrl, `/posts?_where=${where}`)
        assert.equal(result.status, 200)
        assert.deepEqual(result.body, [post2])
      })
    },
  )

  await t.test('{"where":{},"sort":"-views"}', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const result = await bodyOf(baseUrl, '/posts?_sort=-views')
      assert.equal(result.status, 200)
      assert.deepEqual(result.body, [post3, post2, post1])
    })
  })

  await t.test('{"where":{},"page":2,"perPage":2}', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const result = await bodyOf(baseUrl, '/posts?_page=2&_per_page=2')
      assert.equal(result.status, 200)
      assert.deepEqual(result.body, {
        first: 1,
        prev: 1,
        next: null,
        last: 2,
        pages: 2,
        items: 3,
        data: [post3],
      })
    })
  })
})

test('create', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const created = await bodyOf(baseUrl, '/posts', sendJson('POST', { title: 'new post' }))
    assert.equal(created.status, 201)
    assert.equal(created.body.title, 'new post')
    assert.equal(typeof created.body.id, 'string')

    const stored = await bodyOf(baseUrl, '/posts')
    assert.ok(
      stored.body.some((post) => post.id === created.body.id && post.title === 'new post'),
    )

    const customId = await bodyOf(
      baseUrl,
      '/posts',
      sendJson('POST', { title: 'new post', id: 'foo' }),
    )
    assert.equal(customId.status, 201)
    assert.notEqual(customId.body.id, 'foo')
    assert.equal(customId.body.title, 'new post')

    const after = await bodyOf(baseUrl, '/posts')
    assert.equal(
      after.body.some((post) => post.id === 'foo'),
      false,
    )

    const unknown = await bodyOf(baseUrl, '/xxx', sendJson('POST', { title: 'new post' }))
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })
  })
})

test('update', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const replaced = await bodyOf(baseUrl, '/object', sendJson('PUT', { f1: 'bar' }))
    assert.equal(replaced.status, 200)
    assert.deepEqual(replaced.body, { f1: 'bar' })
    assert.deepEqual((await bodyOf(baseUrl, '/object')).body, { f1: 'bar' })

    const unknown = await bodyOf(baseUrl, '/xxx', sendJson('PUT', { f1: 'bar' }))
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })

    const arrayResource = await bodyOf(baseUrl, '/posts', sendJson('PUT', {}))
    assert.equal(arrayResource.status, 404)
    assert.deepEqual(arrayResource.body, { error: 'Not Found' })
    assert.deepEqual((await bodyOf(baseUrl, '/posts')).body, [post1, post2, post3])
  })
})

test('patch', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const patched = await bodyOf(baseUrl, '/object', sendJson('PATCH', { f2: 'bar' }))
    assert.equal(patched.status, 200)
    assert.deepEqual(patched.body, { f1: 'foo', f2: 'bar' })
    assert.deepEqual((await bodyOf(baseUrl, '/object')).body, { f1: 'foo', f2: 'bar' })

    const unknown = await bodyOf(baseUrl, '/xxx', sendJson('PATCH', { f2: 'bar' }))
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })

    const arrayResource = await bodyOf(baseUrl, '/posts', sendJson('PATCH', {}))
    assert.equal(arrayResource.status, 404)
    assert.deepEqual(arrayResource.body, { error: 'Not Found' })
    assert.deepEqual((await bodyOf(baseUrl, '/posts')).body, [post1, post2, post3])
  })
})

test('updateById', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const updated = await bodyOf(
      baseUrl,
      '/posts/1',
      sendJson('PUT', { id: 'xxx', title: 'updated post' }),
    )
    assert.equal(updated.status, 200)
    assert.deepEqual(updated.body, { id: '1', title: 'updated post' })
    assert.deepEqual((await bodyOf(baseUrl, '/posts/1')).body, {
      id: '1',
      title: 'updated post',
    })

    const unknown = await bodyOf(
      baseUrl,
      '/xxx/1',
      sendJson('PUT', { id: 'xxx', title: 'updated post' }),
    )
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })

    const missing = await bodyOf(
      baseUrl,
      '/posts/xxx',
      sendJson('PUT', { id: 'xxx', title: 'updated post' }),
    )
    assert.equal(missing.status, 404)
    assert.deepEqual(missing.body, { error: 'Not Found' })
  })
})

test('patchById', { timeout: 20_000 }, async () => {
  await withServer(data(), async ({ baseUrl }) => {
    const patched = await bodyOf(
      baseUrl,
      '/posts/1',
      sendJson('PATCH', { id: 'xxx', title: 'updated post' }),
    )
    const expected = {
      id: '1',
      title: 'updated post',
      views: 100,
      published: true,
      author: { name: 'foo' },
      tags: ['foo', 'bar'],
    }
    assert.equal(patched.status, 200)
    assert.deepEqual(patched.body, expected)
    assert.deepEqual((await bodyOf(baseUrl, '/posts/1')).body, expected)

    const unknown = await bodyOf(
      baseUrl,
      '/xxx/1',
      sendJson('PATCH', { id: 'xxx', title: 'updated post' }),
    )
    assert.equal(unknown.status, 404)
    assert.deepEqual(unknown.body, { error: 'Not Found' })

    const missing = await bodyOf(
      baseUrl,
      '/posts/xxx',
      sendJson('PATCH', { id: 'xxx', title: 'updated post' }),
    )
    assert.equal(missing.status, 404)
    assert.deepEqual(missing.body, { error: 'Not Found' })
  })
})

test('destroy', { timeout: 90_000 }, async (t) => {
  await t.test('nullifies foreign keys', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const removed = await bodyOf(baseUrl, '/posts/1', { method: 'DELETE' })
      assert.equal(removed.status, 200)
      assert.deepEqual(removed.body, post1)

      const posts = await bodyOf(baseUrl, '/posts')
      assert.deepEqual(posts.body, [post2, post3])
      const comments = await bodyOf(baseUrl, '/comments')
      assert.deepEqual(comments.body, [{ ...comment1, postId: null }])
      assert.deepEqual((await bodyOf(baseUrl, '/object')).body, obj)
    })
  })

  await t.test('deletes dependent resources', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const removed = await bodyOf(baseUrl, '/posts/1?_dependent=comments', {
        method: 'DELETE',
      })
      assert.equal(removed.status, 200)
      assert.deepEqual(removed.body, post1)
      assert.deepEqual((await bodyOf(baseUrl, '/posts')).body, [post2, post3])
      assert.deepEqual((await bodyOf(baseUrl, '/comments')).body, [])
    })
  })

  await t.test('ignores unknown resources', { timeout: 20_000 }, async () => {
    await withServer(data(), async ({ baseUrl }) => {
      const unknown = await bodyOf(baseUrl, '/xxx/1', { method: 'DELETE' })
      assert.equal(unknown.status, 404)
      assert.deepEqual(unknown.body, { error: 'Not Found' })

      const missing = await bodyOf(baseUrl, '/posts/xxx', { method: 'DELETE' })
      assert.equal(missing.status, 404)
      assert.deepEqual(missing.body, { error: 'Not Found' })

      assert.deepEqual((await bodyOf(baseUrl, '/posts')).body, [post1, post2, post3])
      assert.deepEqual((await bodyOf(baseUrl, '/comments')).body, [comment1])
    })
  })
})
