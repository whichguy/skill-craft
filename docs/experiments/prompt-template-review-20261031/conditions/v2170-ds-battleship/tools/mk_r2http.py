import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write
PAGE = "const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); {BODY} } finally { await s.close(); }"
def page(wid, body):
    write(wid, "L.run(async () => {\n  " + PAGE.replace('{BODY}', body) + "\n});")

page('R-2.1', "check(r.status === 200, 'GET / answered ' + r.status); check(r.headers['content-type'] === 'text/html; charset=utf-8', 'content-type was ' + r.headers['content-type']);")
page('R-2.2', "check(r.text.includes('<title>Battleship</title>'), 'the body has no exact <title>Battleship</title>');")
page('R-2.3', "const n = (r.text.match(/data-row=\"\\d\" data-col=\"\\d\"/g) || []).length; check(n === 100, 'cell count in served body was ' + n);")
page('R-2.4', """const rows = {}, cols = {};
    for (const m of r.text.matchAll(/data-row="(\\d+)" data-col="(\\d+)"/g)) { rows[m[1]] = (rows[m[1]] || 0) + 1; cols[m[2]] = (cols[m[2]] || 0) + 1; }
    for (let i = 0; i < 10; i++) { check(rows[i] === 10, 'data-row=' + i + ' appears ' + rows[i] + ' times'); check(cols[i] === 10, 'data-col=' + i + ' appears ' + cols[i] + ' times'); }
    check(Object.keys(rows).length === 10 && Object.keys(cols).length === 10, 'unexpected row/col values ' + Object.keys(rows) + ' / ' + Object.keys(cols));""")
page('R-2.5', "const m = /data-row=\"(\\d+)\" data-col=\"(\\d+)\"/.exec(r.text); check(m && m[1] === '0' && m[2] === '0', 'first cell in document order is ' + (m && m.slice(1, 3)));")
page('R-2.6', """const cells = r.text.match(/<button[^>]*class="cell"[^>]*>/g) || [];
    check(cells.length === 100, 'button.cell count ' + cells.length);
    for (const c of cells) { const m = /aria-label="([^"]+)"/.exec(c); check(m, 'cell without an aria-label: ' + c); check(/\\d/.test(m[1]), 'aria-label does not name coordinates: ' + m[1]); }""")
page('R-2.7', "const bad = [...r.text.matchAll(/\\b(?:src|href)\\s*=\\s*[\"']([^\"']*)[\"']/gi)].map((m) => m[1]).filter((v) => /^(https?:)?\\/\\//i.test(v)); check(bad.length === 0, 'off-origin references: ' + bad);")
page('R-2.8', "check(/role=\"status\"/.test(r.text), 'no role=status element in the served body');")
page('R-2.9', "check(/<button[^>]*>\\s*New game\\s*<\\/button>/.test(r.text), 'no New game button in the served body');")
print('ok')
