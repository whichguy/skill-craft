export const meta = {
  name: 'follow-on-closing-review',
  description: 'Independent review of the follow-on work: four lens reviews of the intention from a neutral brief with a synthesis, plus an adversarial audit of the Round 6 and 7 conclusions against the raw evidence with a completeness critic',
  whenToUse: 'Before closing the follow-on work: get independent critique of the intention and verify the recorded conclusions',
  phases: [
    { title: 'Lenses', detail: 'four independent reviews of the intention from the neutral brief' },
    { title: 'Synthesize', detail: 'merge, dedupe and rank into at most seven recommendations' },
    { title: 'Audit', detail: 'adversarially re-derive the Round 5 to 7 claims from raw evidence' },
    { title: 'Critic', detail: 'what the audit did not cover and what still rests on n of 1 or 2' },
  ],
}

const BRIEF = '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/32a2e7bd-09ac-43f8-9ea2-097196b974e3/scratchpad/astra_brief.md'
const REPO = '/Users/dadleet/src/skill-craft'
const READ_ONLY = 'This is a read-only task: do not edit, create or delete any file under the repository or under /Users/dadleet/e2e-runs, do not commit or push, do not start any model run or E2E harness run, and do not message other sessions. You may read files and run read-only commands (git log, git show, git diff, git cat-file, grep, ls, wc, shasum, one-off python3 -I reads). Scratch files, if you need any, go under /tmp/audit-followon-<your label> only. Return the structured result only.'

const REC_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    headline: { type: 'string' },
    recommendations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          why: { type: 'string' },
          refuting_check: { type: 'string' },
          cost: { type: 'string' },
          value: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['claim', 'why', 'refuting_check', 'cost', 'value'],
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'headline', 'recommendations'],
}

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    recommendations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          rank: { type: 'number' },
          claim: { type: 'string' },
          why: { type: 'string' },
          refuting_check: { type: 'string' },
          cost: { type: 'string' },
          supported_by: { type: 'array', items: { type: 'string' } },
        },
        required: ['rank', 'claim', 'why', 'refuting_check', 'cost', 'supported_by'],
      },
    },
    disagreements: { type: 'array', items: { type: 'string' } },
    stop_doing: { type: 'array', items: { type: 'string' } },
    next_step: { type: 'string' },
  },
  required: ['recommendations', 'disagreements', 'stop_doing', 'next_step'],
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    group: { type: 'string' },
    verdict: { type: 'string', enum: ['holds', 'overstated', 'wrong'] },
    checked: { type: 'array', items: { type: 'string' } },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          fix: { type: 'string' },
        },
        required: ['claim', 'problem', 'evidence', 'severity', 'fix'],
      },
    },
  },
  required: ['group', 'verdict', 'checked', 'issues'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    missing: { type: 'array', items: { type: 'string' } },
    unverified: { type: 'array', items: { type: 'string' } },
    suggestions: { type: 'array', items: { type: 'string' } },
  },
  required: ['missing', 'unverified', 'suggestions'],
}

const LENSES = [
  { key: 'cut', focus: 'Argue the strongest case that this whole direction is not worth the complexity it adds. Say what you would cut and what the smallest valuable version is (questions 1 and 2 of the brief).' },
  { key: 'gate', focus: 'The original idea has a gate: has the feature concluded? Design better ways to decide whether a delivery should be followed up than a model-classified list of leftovers (held-out acceptance checks, spec-versus-behaviour diffs, usage or failure signals from the deployed feature, a reviewer pass, and anything else you can justify). Make each concrete: inputs, who computes it, cost, failure modes (question 3).' },
  { key: 'ideas', focus: 'Propose other ideas for the same intention inside a run (a reflection stage, stronger release verification), between runs (a learning log feeding the next intake) and at the owner level (a review cadence), ranked by expected value and cost (question 4).' },
  { key: 'evidence', focus: 'Find the blind spots in what was measured (priming, small n, model-written classes, one host and model, the harness definitions) and design the single cheapest experiment that would most change the picture, concretely, with the harness the journal describes (test/shiploop_e2e/run.py, custom --prompt runs, readouts) (questions 5 and 6).' },
]

function lensPrompt(l) {
  return 'You are one of four independent reviewers of a piece of engineering work. Read the neutral brief at ' + BRIEF + ' first. Your lens: ' + l.focus +
    ' The repository is at ' + REPO + ' if you want to check anything (design note docs/shiploop-follow-on-run-design-2026-10-31.md, journal docs/shiploop-follow-on-run-journal.md, evidence under docs/experiments/follow-on-*); you do not have to read it to answer. ' +
    'Be critical: say where the intention is wrong, thin or aimed at the wrong target, and do not defend the work. Give at most five recommendations, each with the claim, why, the smallest check or experiment that would refute it, a rough cost and a value (high, medium or low), then the biggest risks you see. Set lens to "' + l.key + '". ' + READ_ONLY
}

const GROUPS = [
  { key: 'round6-numbers', text: 'Round 6 (the recommended-run path on a primed decision). Raw runs: /Users/dadleet/e2e-runs/2026-11-01/follow-on-live2-dacc9b/{link1-a,link1-b,link2-a,link2-b,link3-a,link3-b} (result.json, metrics, .shiploop-runs/*/run/state.md, prompt.txt, work/ checkouts). Compact evidence: ' + REPO + '/docs/experiments/follow-on-recommended-run-20261101/ (README.md, runs.json, readings.txt, verdicts.txt, blocked-questions.txt, link3-changes.txt). Re-derive from the raw files, not from the documents: turns and minutes per run (link1: 172 and 159 turns, 11.5 and 10.6 min; link2: 25 and 25, 1.2 and 1.4; link3: 162 and 144, 12.8 and 11.3); the gates (link1 and link3 all six; link2 four of six with shiploop and committed failing and outcome class BLOCKED); each link-1 handoff accepted on its first complete with exactly one decision entry citing lessons.open_next; link 2 blocked at spec with an awaiting question and options; link 3 follow_on empty in both; plugin tree 3efc9db89059 in all six; link-2 prompt equals the request file and link-3 prompt equals request plus answer.txt. Also check the README claims about rules R1 to R9 and predictions P1 to P10 (what held, what missed) against those facts.' },
  { key: 'round6-instruments', text: 'Round 6 instruments and the printed command. Files: ' + REPO + '/docs/experiments/follow-on-recommended-run-20261101/ (calibrate_checks.py, check_printed_command.py, readout.py, launch.sh, printed-command-link1-a.json and -b.json, requests.md). Claims: calibrate_checks.py reports every status as expected on three variants (run it: it calls no model); check_printed_command.py --self-test passes (run it); the printed command ran as printed on copies of both link-1 checkouts (exit 0, one workspace record, stored request equal to the file minus its last newline) according to the two JSON files; the printed command line in the done packet and report matches the form the code emits (read skills/shiploop/scripts/shiploop_follow_on.py start_command and done_lines); the two readout slips described in the journal (a hash compared with the wrong string; a folder filter that skipped link 3) are real and fixed in the committed readout.py. Do NOT run check_printed_command.py against real run folders.' },
  { key: 'round7-numbers', text: 'Round 7 (the recommended gap on a primed deferral). Raw runs: /Users/dadleet/e2e-runs/2026-11-01/follow-on-gap-d79bc3/{link1-a,link1-b,link2-b}. Compact evidence: ' + REPO + '/docs/experiments/follow-on-recommended-gap-20261101/. Re-derive from raw files: turns and minutes (141, 146, 167 turns; 8.5, 9.6, 9.0 min); all six gates in all three runs; link1-a filed one note and link1-b one gap with request_sentence S3 (check against the numbered sentences in the run request.md that S3 is the sentence asking for --max-length); versions per run from result.json (link 1: skill-craft 2.31.0 / ShipLoop 1.30.0, plugin tree b604dade538e; link 2: 2.32.0 / 1.30.1, tree 6aa0a67b2ac0); link2-b prompt equals link1-b request file; link2-b made --max-length work (hello-wo for 8, hello for 6) and an unknown option still exits 2; link2-b committed SHIPLOOP.md while neither link-1 run did, and the README claim that ShipLoop has committed that index since commit 2cd8f33b30f3056a925e3636f624849aadf61982 (check the commit and its subject). Also check: the 1.30.1 change touches neither skills/shiploop/scripts/shiploop_follow_on.py nor the handoff duty text (git diff 5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a 01d537e9b753aa04859117c1568dfc19f4a0afe7 -- skills/shiploop), and that Backchain 0.7.0 is in the 2.32.0 plugin.' },
  { key: 'docs-consistency', text: 'Consistency and overstatement in the documents. Read ' + REPO + '/docs/shiploop-follow-on-run-design-2026-10-31.md (the order bullet in section 1, section 7 M2a results, M2b, M3 "How to read it", section 9 live row, section 10 D2 row, section 11 U2) and ' + REPO + '/docs/shiploop-follow-on-run-journal.md Rounds 5, 6 and 7 (plans, results, findings F32 to F49, Superseded and Open paragraphs, the After-the-round paragraph). Check every statement marked "as of" against the evidence it cites; flag overstatements such as "a gap delivers unattended" (n of 1), "only a gap could ever run unattended", "gaps appear only when arranged", "the path ran live end to end", statements that are still true only for the build named; check that firm and exploratory labels are justified; check superseded statements are marked; check that every full 40-hex hash cited in these two files resolves (git cat-file -e <hash>^{commit}) and that every cited repository path exists; check table numbers against the README tables in docs/experiments/follow-on-recommended-run-20261101/README.md and docs/experiments/follow-on-recommended-gap-20261101/README.md.' },
  { key: 'release-claims', text: 'The 2.32.1 / 1.30.2 release and the fix. Claims: the fix commit c01c9663a33cb3da30181b9026a8611f22dffc17 changed only skills/shiploop/scripts/shiploop_follow_on.py, test/shiploop-follow-on.test.py and changes/shiploop/follow-on-request-sentences.md; the new test fails on the pre-fix module and passes on the fixed one (show it: copy the pre-fix module from git show c01c9663a33cb3da30181b9026a8611f22dffc17^:skills/shiploop/scripts/shiploop_follow_on.py into a scratch folder under /tmp and compare request_text output for the test rows against the fixed module); the release commit 9273b4cfda87761f4ad002324b238e6d8f755bfb carries only that note (look at its diff stat and CHANGELOG.md entry); CI for that commit finished with success on all its jobs (gh run list/view for whichguy/skill-craft); the installed Claude plugin tree ~/.claude/plugins/cache/whichguy/skill-craft/2.32.1/skills/shiploop is identical to git archive of the release commit plugins/skill-craft/skills/shiploop; the fix commit message carries a No-E2E-Round trailer and that statement is honest (no live run exercised the fix); the tally script docs/experiments/follow-on-build-20261101/tally_follow_on.py passes its --self-test and its figures quoted in the design note M3 paragraph (Round 5: 5 runs, 0 recommending; Round 6: 6 runs, 2 recommending, 4 starts; Round 7: 3 runs, 1 recommending, 1 start) match what it prints for those folders.' },
  { key: 'unprimed-rate', text: 'The evidence for the unprimed rate. Claims: the offline replay (Round 4; docs/experiments/follow-on-replay-20261101/ and the journal) found a decision in 1.2 percent to 1.8 percent of 166 finished runs and no confirmed gap; Round 5 (docs/experiments/follow-on-build-20261101/, runs under /Users/dadleet/e2e-runs/2026-11-01/follow-on-live-436258) had four live runs with lists of 0, 1, 1, 0 entries, all notes; the design D2 and journal F49 reading that gaps seem to appear only on arranged requests. Re-derive the counts from rows.json, compare.py outputs, runs.json and the run folders, state what the denominators are (E2E corpus: small, saturated, every run completes) and whether the sentence "gaps appear only when arranged" follows from them or overreaches.' },
]

function auditPrompt(g) {
  return 'You are an adversarial auditor. Try to REFUTE the claims below by recomputing them from the raw evidence, not by trusting the documents that state them. Default to "overstated" when the evidence supports less than the claim says, and to "wrong" when a number, hash, path or sentence is false. List what you checked, and each issue with the claim, the problem, the evidence you found, a severity and a concrete fix (the replacement sentence or number). If everything holds, say so with verdict "holds" and an empty issues list. Set group to "' + g.key + '". The repository is ' + REPO + '. Claims and sources:\n\n' + g.text + '\n\n' + READ_ONLY
}

async function reviewChain() {
  const raw = await parallel(LENSES.map(l => () => agent(lensPrompt(l), { label: 'lens:' + l.key, phase: 'Lenses', effort: 'high', schema: REC_SCHEMA })))
  const lenses = raw.filter(Boolean)
  if (lenses.length < LENSES.length) log('lenses missing: ' + (LENSES.length - lenses.length) + ' of ' + LENSES.length + ' returned nothing')
  const synthesis = await agent(
    'Merge these independent reviews of the same engineering work into one ranked list of at most seven recommendations: rank, claim, why, the smallest refuting check, cost, and which lenses support it. Dedupe. Where reviewers disagree, record the disagreement instead of averaging it. Add what to stop doing and one recommended next step. Do not add ideas that no lens raised. Reviews as JSON:\n\n' + JSON.stringify(lenses),
    { label: 'synthesize', phase: 'Synthesize', effort: 'high', schema: SYNTH_SCHEMA })
  return { lenses, synthesis }
}

async function auditChain() {
  const raw = await parallel(GROUPS.map(g => () => agent(auditPrompt(g), { label: 'audit:' + g.key, phase: 'Audit', effort: 'high', schema: AUDIT_SCHEMA })))
  const audits = raw.filter(Boolean)
  if (audits.length < GROUPS.length) log('audits missing: ' + (GROUPS.length - audits.length) + ' of ' + GROUPS.length + ' returned nothing')
  const critic = await agent(
    'You are a completeness critic for an audit of the follow-on-list work (Rounds 5 to 7: a recommend-only list in the ShipLoop handoff, live checks on small tasks with primed requests, a patch release, documents). Below are the claim groups that were audited and the audit results as JSON. Say what was not covered (claims, sources, numbers, behaviours), what still rests on n of 1 or 2 although it is worded as firm, and what you would check next. Groups audited: ' + GROUPS.map(g => g.key).join(', ') + '. Results:\n\n' + JSON.stringify(audits) + '\n\nThe repository is ' + REPO + '; ' + READ_ONLY,
    { label: 'critic', phase: 'Critic', effort: 'high', schema: CRITIC_SCHEMA })
  return { audits, critic }
}

const [review, audit] = await Promise.all([reviewChain(), auditChain()])
return { review, audit }
