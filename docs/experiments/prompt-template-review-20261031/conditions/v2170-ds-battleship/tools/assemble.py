import json, os, collections
S = '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship/'
O = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship/'
conds = json.load(open(O + 'conditions.json'))
log = {}
for f in ['log_A.jsonl', 'log_B.jsonl', 'log_C.jsonl']:
    for l in open(S + f):
        r = json.loads(l)
        if 'id' in r: log[r['id']] = r          # later files override: log_C holds the reworked R-10.10
conf = {}
for f in ['log_confA.jsonl', 'log_confB.jsonl']:
    for l in open(S + f):
        r = json.loads(l)
        if 'id' in r: conf[r['id']] = r

SURV = {
 'R-1.1': ('TC_START and SYS_ENTRY (R-1: serve on PORT, "child.exitCode null")', 'W2/S1 (the require.main entry)',
           'assertion too weak: each case checks the child is alive only a few requests after the startup line and none waits, so a process that exits 3 s after starting passes'),
 'R-1.3': ('SYS_PORT_RESOLUTION (comment "an integer from 1 to 65535")', 'W2/S1 (PORT integer 1..65535 else 3000)',
           'boundary absent: the table has one valid port (8081) and one out-of-range value (70000); the edge 65535 is never exercised'),
 'R-1.4': ('SYS_PORT_RESOLUTION (comment "an integer from 1 to 65535")', 'W2/S1 (PORT integer 1..65535 else 3000)',
           'boundary absent: 65536, one above the upper edge, is not in the table (only 70000 is), so an off-by-one upper bound passes'),
 'R-1.5': ('SYS_PORT_RESOLUTION (comment "an integer from 1 to 65535")', 'W2/S1 (PORT integer 1..65535 else 3000)',
           'boundary absent: PORT=1 (the lower edge) is never exercised; zero is, but a lower bound of 2 passes'),
 'R-2.6': ('TC_BROWSER_KEYBOARD (accessible name carries the coordinates) and TC_PAGE (cell markup)', 'W2/S1 (cells served as <button class="cell" data-row data-col aria-label>) and W3/S2 C7',
           'masked by the page script: TC_PAGE reads only the data-row/data-col pairs of the served body, and the keyboard case reads the accessible name from the live DOM, where the script rewrites every cell\'s aria-label at load'),
 'R-2.9': ('TC_PAGE (a) "the page offers a New game control"', 'W2/S1 (New game button in the markup)',
           'assertion too broad: /New game/ matches anywhere in the served text, including the script\'s status strings ("Choose New game to play again"); browser cases click #new-game by id and never read its text'),
 'R-2.12': ('TC_BROWSER_FIRE (the shown count equals the answer\'s shipsRemaining)', 'W3/S2 C5 (prints shipsRemaining)',
            'visibility unchecked: the case reads #remaining\'s textContent, which exists and is correct whether or not the element is visible'),
 'R-2.14': ('TC_BROWSER_FIRE ("the status region says nothing about the shot")', 'W3/S2 C5 names the mark and the count; no criterion names the status announcement of the outcome',
            'assertion too weak: only status !== \'\' is asserted; the outcome word and ships remaining in the status text are never read'),
 'R-2.16': ('TC_BROWSER_LOCK (title: "a shot in flight holds the board")', 'W3/S2 C6 (clicks while a shot is in flight send nothing; the proof pressed two cells under 600 ms latency)',
            'case does not exercise the behaviour: the committed case slows the shot and then clicks New game, never a second cell; the C6 proof\'s two-cells-in-flight check did not become a committed test case'),
 'R-3.6': ('none', 'W1/S1 (criteria name no shared cell; none says ships may touch)',
           'absent: no case or criterion asserts that touching is permitted; only the no-overlap rule is tested, so a placement rule that forbids adjacency passes'),
 'R-3.9': ('TC_PLACEMENT_BUDGET', 'W1/S1 (at most 200 attempts per ship)',
           'assertion too weak: asserts only that a never-fits source throws an Error naming placement within 5 s; the attempt count is not observed, so 5,000 attempts still pass'),
 'R-3.13': ('none (TC_FLEET (b) checks that the default source deals a complete fleet; TC_DETERMINISM covers injected seeds)', 'W1/S1 (createGame default random = Math.random)',
            'absent: HTTP and browser cases inject a seeded source, and the system cases assert only invariant totals, so a server whose default source deals one fixed fleet passes'),
 'R-5.1': ('TC_WALK and TC_COORDINATES (R-5)', 'W2/S2 (server passes row and col to battleship.fire)',
           'orientation-blind assertions: the HTTP walk counts results over all 100 cells and the corner shots check only status codes; neither compares a shot with a known fleet cell, so swapping row and col passes (rules cases call fire(game,row,col) directly and never see the server\'s mapping)'),
 'R-7.7': ('TC_ERROR_TABLE (rows for a fractional row and a quoted row)', 'W2/S3 (400 for a row or col that is not an integer in 0..9)',
           'absent for col: the table pairs row 1.5 and row "1" with col 0 but has no fractional col; TC_COORDINATES covers col only as -1 and 10'),
 'R-7.8': ('TC_ERROR_TABLE (rows for a fractional row and a quoted row)', 'W2/S3 (400 for a row or col that is not an integer in 0..9)',
           'absent for col: no quoted col row in the table; the row-side wrong-type row is tested and its col mirror is not'),
 'R-7.12': ('none', 'W2/S3 (413 over 1 MB)',
            'boundary absent: only the over-limit body (1 MB + 1) is sent; no case sends a large body that must still be accepted, so a 64 KB limit passes'),
 'R-8.1': ('test/battleship.test.js (A-R8.1: "the unit tests, which import only the module")', 'W1/S1 (battleship.js with no require, no I/O)',
           'assertion too weak: importing the module passes while it opens an unref\'d listener; nothing asserts that requiring it opens no socket (TC_START (b) checks only server.js\'s createServer)'),
}
rows = []
counts = collections.Counter()
for c in conds:
    r = dict(c)
    if not c['candidate']:
        r['verdict'] = 'excluded'
        counts['excluded'] += 1
        rows.append(r); continue
    counts['candidates'] += 1
    L = log[c['id']]
    r['witness'] = 'witnesses/%s.js' % c['id']
    r['patch'] = 'patches/%s.patch' % c['id']
    r['witness_exit_original'] = L['witness_exit_original']
    r['witness_exit_variant'] = L['witness_exit_variant']
    r['witness_output_variant'] = L['witness_out_variant']
    r['suite_exit_variant'] = L['suite_exit_variant']
    r['failing_tests'] = L['failing_tests'] if L['suite_exit_variant'] != 0 else []
    ok_w = L['witness_exit_original'] == 0 and L['witness_exit_variant'] != 0
    if not ok_w:
        r['verdict'] = 'unwitnessed'; counts['unwitnessed'] += 1
    else:
        counts['witnessed'] += 1
        if L['suite_exit_variant'] != 0:
            r['verdict'] = 'killed'; counts['killed'] += 1
        else:
            r['verdict'] = 'survived'; counts['survived'] += 1
            cb, st, why = SURV[c['id']]
            r['claimed_by'], r['owning_step'], r['why_survived'] = cb, st, why
            cf = conf[c['id']]
            r['confirmation_rerun'] = dict(witness_exit_original=cf['witness_exit_original'], witness_exit_variant=cf['witness_exit_variant'], suite_exit_variant=cf['suite_exit_variant'])
    rows.append(r)
assert set(SURV) == {r['id'] for r in rows if r['verdict'] == 'survived'}, set(SURV) ^ {r['id'] for r in rows if r['verdict'] == 'survived'}
per_req = collections.OrderedDict()
for r in rows:
    if r['verdict'] in ('killed', 'survived'):
        d = per_req.setdefault(r['requirement'], dict(witnessed=0, killed=0, survived=0))
        d['witnessed'] += 1; d[r['verdict']] += 1
hb = open(S + 'hash_before.txt').read().split()[0]; ha = open(S + 'hash_after.txt').read().split()[0]
res = dict(
    run='~/e2e-runs/20261027/v2170-ds-battleship-759a03 (worktree .shiploop-runs/work-20261027-150517-62d689/worktree)',
    suite_command='cd <copy> && node --test && node --test browser-check/page.js && node --test system-check/system.js  (the run\'s own full local suite per docs/shiploop/environment.md ## Commands; tools/run_suite.sh runs the three and exits 0 only if all three do; the variant verdict is its exit code)',
    baseline_exit=0,
    baseline_summary='unchanged copy: node --test tests 26 pass 26 fail 0; browser-check/page.js tests 8 pass 8 fail 0 (headless Chrome 156); system-check/system.js tests 6 pass 6 fail 0. Re-run unchanged 20 times during the pass (every 6 conditions) and at the end on both copies: all exit 0.',
    original_hash_before=hb, original_hash_after=ha, original_unchanged=(hb == ha),
    witness_howto='WORK=<checkout> node witnesses/R-n.k.js (exit 0 = condition holds). Helpers: witnesses/_lib.js, witnesses/_cdp.js (own CDP driver). Patches apply with git apply to the unchanged copy.',
    conditions=rows,
    counts=dict(candidates=counts['candidates'], witnessed=counts['witnessed'], killed=counts['killed'], survived=counts['survived'], unwitnessed=counts['unwitnessed'], excluded=counts['excluded']),
    kill_rate=round(counts['killed'] / counts['witnessed'], 4), survival_rate=round(counts['survived'] / counts['witnessed'], 4),
    per_requirement=per_req,
    survivors_by_kind=dict(collections.Counter(r['kind'] for r in rows if r['verdict'] == 'survived')),
    survivors_claimed_vs_absent=dict(claimed_weak=sum(1 for r in rows if r['verdict'] == 'survived' and not r['claimed_by'].startswith('none')),
                                     absent=sum(1 for r in rows if r['verdict'] == 'survived' and r['claimed_by'].startswith('none'))),
    notes=[
      'Conditions were written from the frozen requirements text before opening repo or run_dir (conditions.sha256).',
      'The copy is a plain directory with its own git repo (the original .git file points into the source checkout, so it was removed in the copy); the original was never edited.',
      'R-10.10: the first variant (setImmediate gap) never produced two 200s and the witness HELD on it, so it was reworked (40 ms gap; patch regenerated) and re-run: killed. All other verdicts come from the first pass.',
      'R-10.11 reuses the R-5.12 patch (a refused repeat shot un-fires the cell): the rules module is state-derived, so no independent "counted twice" violation exists.',
      'Several variants break neighbouring conditions as well (e.g. R-1.2 ignores PORT; R-2.16 and R-2.17 touch the same lock; R-3.8 and R-3.13 both fix the fleet; R-6.x share the game-over flag; R-10.8/R-10.9 use module-level state); the witness for each id checks only its own condition.',
      'R-7.22/R-7.23/R-7.24/R-7.25 variants make the process crash. R-7.23 is killed because the in-process server inside test/server.test.js crashes the test file (file-level failure, no individual case named).',
      'R-3.9 witness assumes three random draws per placement attempt (orientation, row, column) to count attempts from the injected source.',
      'Witnesses for the fallback port (R-1.6..R-1.12) accept either a listener on 3000 (lsof of the child) or the in-use refusal naming 3000, because other workers may hold port 3000.',
      'Browser witnesses use headless Chrome through their own DevTools driver; the injected-random server makes the fleet known to the witness via the rules module\'s createGame with the same seed.',
    ])
json.dump(res, open(O + 'results.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(res['counts']), res['kill_rate'], res['survival_rate'], res['original_unchanged'])
print(json.dumps(per_req))
print(res['survivors_by_kind'], res['survivors_claimed_vs_absent'])
