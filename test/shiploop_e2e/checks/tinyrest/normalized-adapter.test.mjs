import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

import { asJson, http, sendJson, withServer } from './harness.mjs'

const DEFAULT_SCHEMA_PATH = './node_modules/json-server/schema.json'

test('read removes $schema and normalizes ids', { timeout: 20_000 }, async () => {
  await withServer(
    {
      $schema: './custom/schema.json',
      posts: [{ id: 1 }, { title: 'missing id' }],
      profile: { name: 'x' },
    },
    async ({ baseUrl }) => {
      const posts = await http(baseUrl, '/posts')
      assert.equal(posts.status, 200, posts.text)
      const body = asJson(posts)
      assert.ok(Array.isArray(body))
      assert.equal(body.length, 2)
      assert.equal(body[0].id, '1')
      assert.equal(typeof body[0].id, 'string')
      assert.equal(body[1].title, 'missing id')
      assert.equal(typeof body[1].id, 'string')
      assert.notEqual(body[1].id, '')

      const again = asJson(await http(baseUrl, '/posts'))
      assert.equal(again[1].id, body[1].id)

      const profile = await http(baseUrl, '/profile')
      assert.equal(profile.status, 200)
      assert.deepEqual(asJson(profile), { name: 'x' })

      const schema = await http(baseUrl, '/$schema')
      assert.equal(schema.status, 404)
      assert.deepEqual(asJson(schema), { error: 'Not Found' })
    },
  )
})

test('write always overwrites $schema', { timeout: 20_000 }, async () => {
  await withServer(
    {
      $schema: './custom/schema.json',
      posts: [{ id: '1' }],
    },
    async ({ baseUrl, file }) => {
      const created = await http(baseUrl, '/posts', sendJson('POST', { title: 'next' }))
      assert.equal(created.status, 201, created.text)

      const onDisk = JSON.parse(fs.readFileSync(file, 'utf8'))
      assert.equal(onDisk.$schema, DEFAULT_SCHEMA_PATH)
      assert.notEqual(onDisk.$schema, './custom/schema.json')
      assert.equal(onDisk.posts[0].id, '1')
      assert.equal(onDisk.posts.length, 2)
    },
  )
})
