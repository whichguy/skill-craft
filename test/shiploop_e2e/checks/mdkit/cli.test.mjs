import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

function commandParts() {
  const cmd = process.env.APP_CMD;
  const match = cmd.match(/^(\S+)\s+([\s\S]+)$/);
  if (!match) return [cmd];
  return [match[1], match[2]];
}

function run(args, { input } = {}) {
  const parts = commandParts();
  return new Promise((resolve, reject) => {
    const child = spawn(parts[0], [...parts.slice(1), ...args], { stdio: ['pipe', 'pipe', 'pipe'] });
    const out = [];
    const err = [];
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('cli timed out'));
    }, 10000);
    child.stdout.on('data', (chunk) => out.push(chunk));
    child.stderr.on('data', (chunk) => err.push(chunk));
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({
        code,
        stdout: Buffer.concat(out).toString('utf8'),
        stderr: Buffer.concat(err).toString('utf8'),
      });
    });
    child.stdin.end(input ?? '');
  });
}

async function withFixture(runCase) {
  const dir = await mkdtemp(join(tmpdir(), 'marked-oracle-'));
  try {
    await writeFile(join(dir, 'package.json'), '{"type":"module"}\n');
    await writeFile(join(dir, 'config.js'), 'export default { breaks: true };\n');
    await writeFile(join(dir, 'config#hash.js'), 'export default { breaks: true };\n');
    await writeFile(join(dir, 'input.md'), '# file\n');
    await runCase(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test('-s renders a heading from the argument', async () => {
  const result = await run(['-s', '# test']);
  assert.equal(result.code, 0);
  assert.equal(result.stdout, '<h1>test</h1>\n\n');
});

test('--string renders a heading from the argument', async () => {
  const result = await run(['--string', '# test']);
  assert.equal(result.code, 0);
  assert.equal(result.stdout, '<h1>test</h1>\n\n');
});

test('-c loads a config module that turns on breaks', async () => {
  await withFixture(async (dir) => {
    const result = await run(['-c', join(dir, 'config.js'), '-s', 'line1\nline2']);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<p>line1<br>line2</p>\n\n');
  });
});

test('--config loads a config module that turns on breaks', async () => {
  await withFixture(async (dir) => {
    const plain = await run(['-s', 'line1\nline2']);
    const result = await run(['--config', join(dir, 'config.js'), '-s', 'line1\nline2']);
    assert.equal(plain.code, 0);
    assert.equal(plain.stdout, '<p>line1\nline2</p>\n\n');
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<p>line1<br>line2</p>\n\n');
  });
});

test('--config loads a module whose filename contains a hash', async () => {
  await withFixture(async (dir) => {
    const result = await run(['--config', join(dir, 'config#hash.js'), '-s', 'line1\nline2']);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<p>line1<br>line2</p>\n\n');
  });
});

test('missing --config exits with a failure status and no html', async () => {
  await withFixture(async (dir) => {
    const ok = await run(['--config', join(dir, 'config.js'), '-s', 'line1\nline2']);
    const missing = await run(['--config', join(dir, 'does-not-exist.js'), '-s', 'line1\nline2']);
    assert.equal(ok.code, 0);
    assert.match(ok.stdout, /<br>/);
    assert.equal(missing.code, 1);
    assert.equal(missing.stdout, '');
    assert.ok(missing.stderr.length > 0);
  });
});

test('a positional file is compiled', async () => {
  await withFixture(async (dir) => {
    const result = await run([join(dir, 'input.md')]);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<h1>file</h1>\n\n');
  });
});

test('a missing positional file exits with a failure status and no html', async () => {
  await withFixture(async (dir) => {
    const ok = await run([join(dir, 'input.md')]);
    const missing = await run([join(dir, 'does-not-exist.md')]);
    assert.equal(ok.code, 0);
    assert.match(ok.stdout, /<h1>file<\/h1>/);
    assert.equal(missing.code, 1);
    assert.equal(missing.stdout, '');
    assert.ok(missing.stderr.length > 0);
  });
});

test('a missing --input file exits with a failure status and no html', async () => {
  await withFixture(async (dir) => {
    const ok = await run(['--input', join(dir, 'input.md')]);
    const missing = await run(['--input', join(dir, 'does-not-exist.md')]);
    assert.equal(ok.code, 0);
    assert.equal(ok.stdout, '<h1>file</h1>\n\n');
    assert.equal(missing.code, 1);
    assert.equal(missing.stdout, '');
    assert.ok(missing.stderr.length > 0);
  });
});

test('--input compiles a file', async () => {
  await withFixture(async (dir) => {
    const result = await run(['-i', join(dir, 'input.md')]);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<h1>file</h1>\n\n');
  });
});

test('stdin is compiled when no path is given', async () => {
  const result = await run([], { input: '# test\n' });
  assert.equal(result.code, 0);
  assert.equal(result.stdout, '<h1>test</h1>\n\n');
});

test('the last positional file is the one compiled', async () => {
  await withFixture(async (dir) => {
    const result = await run([join(dir, 'does-not-exist.md'), join(dir, 'input.md')]);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '<h1>file</h1>\n\n');
  });
});
