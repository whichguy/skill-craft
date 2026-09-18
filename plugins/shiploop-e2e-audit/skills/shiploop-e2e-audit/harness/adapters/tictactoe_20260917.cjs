'use strict';
// Independently mapped September 17 returned TTT sample. Unsupported markup
// fails explicitly. Extend only after inspecting another returned candidate.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');

exports.prepare = async repo => {
  const files = Object.fromEntries(['Index.html', 'JavaScript.html', 'Code.gs'].map(name => [name, fs.readFileSync(path.join(repo, name), 'utf8')]));
  const supported = {
    'Code.gs': '445dbd4aac83e8d72f4af7cb69fc278c541651478422015b1792cdb0f0e2ccdf',
    'Index.html': 'd78d9f637726c41cc48986ee65f3a42f0329a30c89946eebed7ed5bffcd5ac7c',
    'JavaScript.html': 'edca5fd9b77391a6467cc738fc2d3d44501f29b330864490cdbd07ebc8ed6096',
  };
  for (const [name, expected] of Object.entries(supported)) {
    if (hash(files[name]) !== expected) throw new Error('Unmapped candidate revision: ' + name);
  }
  const expression = /<\?!=\s*include\(['"]JavaScript['"]\);?\s*\?>/g;
  if ((files['Index.html'].match(expression) || []).length !== 1) throw new Error('Unsupported TTT include shape');
  const html = files['Index.html'].replace(expression, () => files['JavaScript.html']);
  if (html.includes('<?')) throw new Error('Unresolved template expression');
  return { html, source: Object.fromEntries(Object.entries(files).map(([name, value]) => [name, hash(value)])) };
};

exports.perform = async (page, action) => {
  if (action.type === 'reset') return page.locator('#new-game').click();
  if (action.type === 'move' && Number.isInteger(action.cell) && action.cell >= 0 && action.cell < 9) {
    // A disabled occupied/terminal cell correctly rejects an ordinary click.
    const cell = page.locator(`#board [data-index="${action.cell}"]`);
    if (await cell.isDisabled()) return;
    return cell.click();
  }
  throw new Error('Unsupported TTT action');
};

exports.observe = async (page, previous) => {
  const raw = await page.evaluate(() => ({
    board: [...document.querySelectorAll('#board [data-index]')].sort((a, b) => Number(a.dataset.index) - Number(b.dataset.index)).map(el => el.textContent.trim()),
    status: document.querySelector('#status').textContent.trim(),
  }));
  if (raw.board.length !== 9) throw new Error('Unsupported board');
  const turn = /^([XO]) to move$/.exec(raw.status);
  const win = /^([XO]) wins$/.exec(raw.status);
  let active_player, outcome;
  if (turn) { active_player = turn[1]; outcome = 'playing'; }
  else if (win) { active_player = win[1]; outcome = win[1]; }
  else if (raw.status === 'Draw') { active_player = null; outcome = 'draw'; }
  else if (['Square occupied', 'Game over', 'Invalid square'].includes(raw.status) && previous) {
    active_player = previous.active_player; outcome = previous.outcome;
  } else throw new Error('Unsupported visible status: ' + raw.status);
  // The inspected baseline has no highlight/suggestion UI. These values describe
  // that known baseline; a later feature needs an independently inspected mapping.
  return { board: raw.board, active_player, outcome, legal_highlights: [], recommended_move: null };
};
