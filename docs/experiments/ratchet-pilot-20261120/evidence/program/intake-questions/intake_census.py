#!/usr/bin/env python3
"""Census of intake key-question ledgers in archived ShipLoop E2E run folders.

READ ONLY over the archives. Writes census.json and census.txt.

Usage: intake_census.py OUT_DIR
Layout discovered:
  <harness run folder>/invocation.json            case, host, model, effort
  <harness run folder>/.shiploop-runs/<work-id>/run/results/nav-*.md   (or <folder>/shiploop-run/results/)
  each result holds a ```shiploop-state JSON block with "stage" and "result"
  intake result carries result.question_categories and result.questions
  accepted knowledge: <folder>/work/docs/shiploop/*.md (spec.md ...), or the worktree copy,
                      <run>/current-spec.md, <folder>/spec-accepted.md
"""
import json, os, re, sys, collections

ROOT = __import__('os').path.expanduser('~')
SCAN_ROOTS = ['e2e-runs', 'e2e-runs-sdlc12']
PRUNE = {'node_modules', '.git', 'home', 'worktree', 'consumer-check', 'scratch'}
STOP = set('''about above after again against being below between could does doing during each from have having here
into itself just more most other over same should some such than that their them then there these they this those through
under until very what when where which while with would your must will also only both either whose without within
make made makes using used uses want need needs'''.split())


def short(p):
    return p.replace(ROOT + '/', '~/') if p.startswith(ROOT + '/') else p


def find_result_dirs():
    out = []
    for r in SCAN_ROOTS:
        base = os.path.join(ROOT, r)
        for dp, dn, fn in os.walk(base):
            rel = os.path.relpath(dp, base)
            top = rel.split(os.sep)[0]
            if r == 'e2e-runs' and (top.startswith('ratchet-')):
                dn[:] = []
                continue
            dn[:] = [d for d in dn if d not in PRUNE and not (r == 'e2e-runs' and dp == base and d.startswith('ratchet-'))]
            if os.path.basename(dp) == 'results' and os.path.basename(os.path.dirname(dp)) in ('run', 'shiploop-run'):
                out.append(dp)
                dn[:] = []
    return sorted(out)


STATE_RE = re.compile(r'```shiploop-state\n(.*?)\n```', re.S)


def parse_result(path):
    try:
        t = open(path, errors='replace').read()
    except OSError:
        return None, ''
    m = STATE_RE.search(t)
    if not m:
        return None, t
    try:
        return json.loads(m.group(1)), t
    except Exception:
        return None, t


def harness_root(run_dir):
    """run_dir = .../run or .../shiploop-run (the folder holding results/)."""
    p = os.path.dirname(run_dir)
    q = p
    while q and q != '/':
        if os.path.exists(os.path.join(q, 'invocation.json')):
            return q
        q = os.path.dirname(q)
    # fallback: parent of .shiploop-runs or shiploop-run
    cur = run_dir
    while cur != '/':
        if os.path.basename(cur) in ('.shiploop-runs', 'shiploop-run'):
            return os.path.dirname(cur)
        cur = os.path.dirname(cur)
    return os.path.dirname(run_dir)


def scope_of(rel):
    top = rel.split('/')[0]
    if top == 'e2e-runs-sdlc12':
        return 'in_scope'
    parts = rel.split('/')
    d = parts[1] if len(parts) > 1 else ''
    if re.fullmatch(r'2026-(10-31|11-\d\d)', d) or d in ('20261101', '20261110'):
        return 'in_scope'
    return 'other_undated_folder'


def run_date(run_dir, rel):
    m = re.search(r'/work-(\d{4})(\d\d)(\d\d)-', run_dir)
    if m:
        return '%s-%s-%s' % m.groups()
    m = re.search(r'/(\d{4}-\d\d-\d\d)/', '/' + rel + '/')
    if m:
        return m.group(1)
    m = re.search(r'/(\d{4})(\d\d)(\d\d)/', '/' + rel + '/')
    if m:
        return '%s-%s-%s' % m.groups()
    return None


def read_files(paths):
    out = []
    for p in paths:
        try:
            out.append((p, open(p, errors='replace').read()))
        except OSError:
            pass
    return out


def knowledge_files(hroot, run_dir):
    paths = []
    k = os.path.join(hroot, 'work', 'docs', 'shiploop')
    cands = [k]
    # worktree copies, only if the work copy is missing
    runs = os.path.dirname(run_dir) if os.path.basename(run_dir) == 'run' else None
    if runs:
        cands.append(os.path.join(runs, 'worktree', 'docs', 'shiploop'))
    chosen = None
    for c in cands:
        if os.path.isdir(c):
            chosen = c
            break
    if chosen:
        for dp, dn, fn in os.walk(chosen):
            dn[:] = [d for d in dn if d not in PRUNE]
            for f in fn:
                if f.endswith('.md'):
                    paths.append(os.path.join(dp, f))
    for extra in (os.path.join(run_dir, 'current-spec.md'), os.path.join(hroot, 'spec-accepted.md')):
        if os.path.isfile(extra):
            paths.append(extra)
    return paths, chosen


def content_words(*texts):
    ws = set()
    for t in texts:
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-\.]{4,}", t or ''):
            w = w.lower().strip('.-_')
            if len(w) >= 5 and w not in STOP:
                ws.add(w)
    return ws


def id_re(qid):
    return re.compile(r'(?<![A-Za-z0-9_])' + re.escape(qid) + r'(?![A-Za-z0-9_])')


def match_question(q, texts):
    """texts: list of (label, text). Returns dict with id_hits, kw_hits, where."""
    qid = q.get('id', '')
    rx = id_re(qid)
    words = content_words(q.get('question'), q.get('default'), q.get('changes'))
    qwords = content_words(q.get('question'))
    need = 2 if len(qwords) >= 3 else 1
    id_hits = []
    kw_hits = []
    for label, t in texts:
        tl = t.lower()
        for m in rx.finditer(t):
            id_hits.append(label)
            win = tl[max(0, m.start() - 300): m.end() + 300]
            found = {w for w in qwords if w in win} | {w for w in words if w in win and w in qwords}
            # count distinct question words in the window
            if len(found) >= need:
                kw_hits.append((label, sorted(found)[:6], t[max(0, m.start() - 80): m.end() + 120].replace('\n', ' ')))
    return {'id_hits': id_hits, 'kw_hits': kw_hits}


OPEN_RES = {
    'open_gap': re.compile(r'open[ -]gaps?', re.I),
    'open_question': re.compile(r'open[ -]questions?', re.I),
    'awaiting': re.compile(r'\bawaiting\b', re.I),
    'open_marker': re.compile(r'(^|\n)\s*[-*>\d\.\)\s]*\**Open\**:', re.I),
}
ASSUM_RE = re.compile(r'assum', re.I)
NEG_RE = re.compile(r'(\bno\b|\bnone\b|\bnot\b|\bwithout\b|\bzero\b)[^.\n]{0,40}open[ -](gaps?|questions?)|open[ -](gaps?|questions?)\W{0,3}(:\s*)?(none|no\b)', re.I)
HEAD_RE = re.compile(r'^#+\s*open[ -](gaps?|questions?)\b.*$', re.I | re.M)


def heading_entries(t):
    """entries (bullets) under an 'Open gaps/questions' heading: (real, none)"""
    real = none = 0
    for m in HEAD_RE.finditer(t):
        rest = t[m.end():].split('\n')
        for ln in rest[1:]:
            if re.match(r'^#+\s', ln):
                break
            b = re.match(r'^\s*(?:[-*]|\d+[.)])\s+(.*)$', ln)
            if b:
                if re.match(r'(none|nothing|n/a|no )', b.group(1).strip(), re.I):
                    none += 1
                else:
                    real += 1
    return real, none


def count_lines(rx, t):
    return sum(1 for ln in t.split('\n') if rx.search(ln))


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rdirs = find_result_dirs()
    runs = []
    for rd in rdirs:
        files = sorted(f for f in os.listdir(rd) if f.endswith('.md'))
        intake = None
        parsed = {}
        for f in files:
            j, t = parse_result(os.path.join(rd, f))
            parsed[f] = (j, t)
            if j and j.get('stage') == 'intake' and 'question_categories' in j.get('result', {}):
                intake = (f, j)
        if not intake:
            continue
        run_dir = os.path.dirname(rd)
        hroot = harness_root(run_dir)
        rel = os.path.relpath(hroot, ROOT) if hroot.startswith(ROOT) else hroot
        inv = {}
        try:
            inv = json.load(open(os.path.join(hroot, 'invocation.json')))
        except Exception:
            pass
        # timeline order
        accepted = {}
        try:
            accepted = json.load(open(os.path.join(run_dir, 'timeline.json'))).get('accepted', {})
        except Exception:
            pass
        ifile, ij = intake
        iid = 'nav-' + ij['action'].replace('nav-', '') if ij.get('action') else None
        it_time = accepted.get(ij.get('action'))
        res = ij['result']
        cats = res['question_categories']
        qs = res.get('questions', [])
        # later results
        later = []
        for f, (j, t) in parsed.items():
            if f == ifile or not j:
                continue
            if j.get('stage') == 'intake':
                continue
            at = accepted.get(j.get('action'))
            if it_time and at and at < it_time:
                continue
            later.append((f, j, t))
        # texts for matching
        res_texts = [('result:' + (j.get('stage') or '?'), t) for f, j, t in later]
        kfiles, kdir = knowledge_files(hroot, run_dir)
        know = read_files(kfiles)
        know_texts = [('knowledge:' + os.path.relpath(p, hroot if p.startswith(hroot) else run_dir), t) for p, t in know]
        # notes/fields (secondary)
        nf_paths = []
        for sub in ('notes', 'fields'):
            d = os.path.join(run_dir, sub)
            if os.path.isdir(d):
                nf_paths += [os.path.join(d, x) for x in sorted(os.listdir(d)) if x.endswith('.md')]
        nf_texts = [('notes:' + os.path.basename(p), t) for p, t in read_files(nf_paths)]
        qrecs = []
        for q in qs:
            m1 = match_question(q, res_texts + know_texts)
            m2 = match_question(q, nf_texts)
            qrecs.append({
                'id': q.get('id'), 'category': q.get('category'), 'route': q.get('route'),
                'question': q.get('question'), 'default': q.get('default'), 'blocks': q.get('blocks'),
                'changes': q.get('changes'),
                'id_only': bool(m1['id_hits']), 'id_plus_words': bool(m1['kw_hits']),
                'id_hit_where': sorted(set(m1['id_hits'])),
                'kw_example': m1['kw_hits'][0][2] if m1['kw_hits'] else None,
                'kw_where': sorted({x[0] for x in m1['kw_hits']}),
                'notes_id_only': bool(m2['id_hits']), 'notes_id_plus_words': bool(m2['kw_hits']),
            })
        # open gaps
        og = collections.Counter()
        awaiting_struct = 0
        neg = collections.Counter()
        head_real = head_none = 0
        og_examples = {}
        assum_struct = 0
        unverified_struct = 0
        for f, j, t in later:
            r = j.get('result', {})
            if isinstance(r.get('assumptions'), list):
                assum_struct += len(r['assumptions'])
            if 'awaiting' in r:
                awaiting_struct += 1
            if isinstance(r.get('unverified'), list):
                unverified_struct += len(r['unverified'])
            for k, rx in OPEN_RES.items():
                n = count_lines(rx, t)
                if n:
                    og['result_' + k] += n
                    neg['result'] += count_lines(NEG_RE, t) if k != 'open_marker' else 0
                    og_examples.setdefault('result_' + k, next(ln.strip()[:200] for ln in t.split('\n') if rx.search(ln)))
        assum_lines_know = 0
        for label, t in know_texts:
            for k, rx in OPEN_RES.items():
                n = count_lines(rx, t)
                if n:
                    og['knowledge_' + k] += n
                    og_examples.setdefault('knowledge_' + k, next(ln.strip()[:200] for ln in t.split('\n') if rx.search(ln)))
            assum_lines_know += count_lines(ASSUM_RE, t)
            a, b = heading_entries(t)
            head_real += a
            head_none += b
            neg['knowledge'] += count_lines(NEG_RE, t)
        route_ct = collections.Counter(q.get('route') for q in qs)
        runs.append({
            'run_folder': short(hroot),
            'scope': scope_of(rel),
            'ledger_run_dir': short(run_dir),
            'intake_result': ifile,
            'case': inv.get('case'), 'host': inv.get('host'), 'model': inv.get('model'), 'effort': inv.get('effort'),
            'shiploop_version': (inv.get('versions') or {}).get('shiploop_version') if isinstance(inv.get('versions'), dict) else None,
            'plugin_version': (inv.get('versions') or {}).get('plugin_version') if isinstance(inv.get('versions'), dict) else None,
            'date': run_date(run_dir, rel),
            'request_headline': res.get('headline'),
            'categories_total': len(cats),
            'categories_apply': sum(1 for c in cats if c.get('applies') == 'yes'),
            'categories_no': sum(1 for c in cats if c.get('applies') == 'no'),
            'n_questions': len(qs),
            'by_route': dict(route_ct),
            'later_results': len(later),
            'later_stages': sorted({j.get('stage') for f, j, t in later}),
            'knowledge_dir': short(kdir) if kdir else None,
            'knowledge_files': [short(p) for p in kfiles],
            'has_spec': any(os.path.basename(p) in ('spec.md', 'current-spec.md', 'spec-accepted.md') for p in kfiles),
            'questions': qrecs,
            'open': {
                'structured_assumptions_in_later_results': assum_struct,
                'structured_unverified_in_later_results': unverified_struct,
                'knowledge_lines_with_assum': assum_lines_know,
                'structured_awaiting_in_later_results': awaiting_struct,
                'knowledge_open_heading_entries_real': head_real,
                'knowledge_open_heading_entries_none': head_none,
                'negated_mention_lines_approx': dict(neg),
                'regex_line_counts': dict(og),
                'regex_examples': og_examples,
                'any_open_gap_question_or_awaiting': any(og.get(k, 0) for k in og if k.split('_', 1)[1] in ('open_gap', 'open_question', 'awaiting')) or awaiting_struct > 0 or (head_real + head_none) > 0,
                'any_real_open_entry': awaiting_struct > 0 or head_real > 0,
                'any_open_marker': any(og.get(k, 0) for k in og if k.endswith('open_marker')),
                'any_assumption_entry': assum_struct > 0 or assum_lines_know > 0,
            },
        })
    open(os.path.join(out_dir, 'census.json'), 'w').write(json.dumps(runs, indent=1).replace(ROOT + '/', '~/'))
    write_text(runs, os.path.join(out_dir, 'census.txt'))


ROUTES = ['inspect', 'research', 'experiment', 'default', 'person']


def totals(rs):
    t = {'runs': len(rs), 'questions': 0, 'categories_apply': 0, 'by_route': collections.Counter(),
         'ref_id_only': collections.Counter(), 'ref_id_words': collections.Counter(),
         'ref_notes_id_only': collections.Counter(), 'ref_notes_id_words': collections.Counter(),
         'runs_open_gap_q_await': 0, 'runs_open_marker': 0, 'runs_struct_assum': 0, 'runs_any_assum_entry': 0,
         'runs_with_spec': 0, 'runs_zero_questions': 0, 'runs_awaiting_struct': 0, 'runs_heading_real': 0, 'runs_heading_any': 0, 'runs_real_open': 0, 'id_where': collections.Counter(), 'runs_discovery_ids': 0}
    for r in rs:
        t['questions'] += r['n_questions']
        t['categories_apply'] += r['categories_apply']
        if r['n_questions'] == 0:
            t['runs_zero_questions'] += 1
        for q in r['questions']:
            rt = q['route']
            t['by_route'][rt] += 1
            t['ref_id_only'][rt] += q['id_only']
            t['ref_id_words'][rt] += q['id_plus_words']
            t['ref_notes_id_only'][rt] += q['notes_id_only']
            t['ref_notes_id_words'][rt] += q['notes_id_plus_words']
        o = r['open']
        t['runs_open_gap_q_await'] += o['any_open_gap_question_or_awaiting']
        t['runs_open_marker'] += o['any_open_marker']
        t['runs_struct_assum'] += o['structured_assumptions_in_later_results'] > 0
        t['runs_any_assum_entry'] += o['any_assumption_entry']
        t['runs_with_spec'] += r['has_spec']
        t['runs_awaiting_struct'] += o['structured_awaiting_in_later_results'] > 0
        t['runs_heading_real'] += o['knowledge_open_heading_entries_real'] > 0
        t['runs_heading_any'] += (o['knowledge_open_heading_entries_real'] + o['knowledge_open_heading_entries_none']) > 0
        t['runs_real_open'] += o['any_real_open_entry']
        t['runs_discovery_ids'] += any('result:discovery' in q['id_hit_where'] for q in r['questions'])
        for q in r['questions']:
            for w in q['id_hit_where']:
                t['id_where'][w.split('/')[0] if w.startswith('knowledge') else w] += 1
    return t


def fmt_totals(name, rs):
    t = totals(rs)
    L = ['--- %s: %d runs with a ledger ---' % (name, t['runs'])]
    L.append('categories applying (sum): %d; questions (sum): %d; runs with zero questions: %d; runs with a spec file found: %d'
             % (t['categories_apply'], t['questions'], t['runs_zero_questions'], t['runs_with_spec']))
    routes = ROUTES + sorted(set(t['by_route']) - set(ROUTES), key=str)
    L.append('%-12s %8s %12s %16s %14s %18s' % ('route', 'asked', 'id_in_later', 'id+words_later', 'id_in_notes', 'id+words_notes'))
    for rt in routes:
        L.append('%-12s %8d %12d %16d %14d %18d' % (rt, t['by_route'][rt], t['ref_id_only'][rt], t['ref_id_words'][rt],
                                                    t['ref_notes_id_only'][rt], t['ref_notes_id_words'][rt]))
    L.append('%-12s %8d %12d %16d %14d %18d' % ('ALL', sum(t['by_route'].values()), sum(t['ref_id_only'].values()),
                                                sum(t['ref_id_words'].values()), sum(t['ref_notes_id_only'].values()),
                                                sum(t['ref_notes_id_words'].values())))
    L.append('runs with any "open gap"/"open question"/"awaiting" line in later results or knowledge: %d' % t['runs_open_gap_q_await'])
    L.append('runs with an "Open:" marker line: %d' % t['runs_open_marker'])
    L.append('runs with a structured `awaiting` result field (a question to the requester): %d' % t['runs_awaiting_struct'])
    L.append('runs whose knowledge files have an "Open gaps/questions" heading: %d; of which with at least one non-"None" entry: %d' % (t['runs_heading_any'], t['runs_heading_real']))
    L.append('runs with a real open entry (structured awaiting, or non-None bullet under an Open gaps/questions heading): %d' % t['runs_real_open'])
    L.append('runs whose discovery result cites at least one intake Q-id: %d' % t['runs_discovery_ids'])
    L.append('where the Q-id mentions were found (question-mentions, by file kind): %s' % dict(t['id_where']))
    L.append('runs with structured `assumptions` entries in later results: %d' % t['runs_struct_assum'])
    L.append('runs with any assumption entry (structured, or a knowledge line mentioning "assum"): %d' % t['runs_any_assum_entry'])
    return L


def write_text(runs, path):
    L = []
    L.append('Intake key-question ledger census (read-only over archives)')
    L.append('Match rules: id = literal token Qn (no adjacent alphanumerics) in the same run\'s later-stage result files (stage != intake, accepted after intake when timeline.json says)')
    L.append('and in its knowledge files (work/docs/shiploop/*.md, or the worktree copy; current-spec.md; spec-accepted.md).')
    L.append('id+words = same, and at least 2 distinct content words (>=5 letters) of the question text (1 if it has <3 such words) occur within 300 chars either side of the token.')
    L.append('notes columns: the same test over run/notes/*.md and run/fields/*.md (extra, not asked).')
    L.append('')
    inscope = [r for r in runs if r['scope'] == 'in_scope']
    other = [r for r in runs if r['scope'] != 'in_scope']
    L += fmt_totals('IN SCOPE (dated folders 2026-10-31..2026-11-15, 20261101, 20261110, and e2e-runs-sdlc12)', inscope)
    L.append('')
    L += fmt_totals('OTHER undated folders under e2e-runs (not named in the brief)', other)
    L.append('')
    L += fmt_totals('ALL', runs)
    L.append('')
    # by root / folder
    L.append('=== Runs with a ledger by top-level folder ===')
    c = collections.Counter()
    for r in runs:
        rel = r['run_folder'].replace('~/', '')
        parts = rel.split('/')
        c[parts[0] + '/' + parts[1]] += 1
    for k, v in sorted(c.items()):
        L.append('%4d  %s' % (v, k))
    L.append('')
    L.append('=== By case / host / model / effort (in scope) ===')
    c = collections.Counter((r['case'], r['host'], r['model'], r['effort']) for r in inscope)
    for k, v in sorted(c.items(), key=lambda x: str(x)):
        L.append('%4d  %s' % (v, ' | '.join(str(x) for x in k)))
    L.append('')
    L.append('=== By case / host / model / effort (other) ===')
    c = collections.Counter((r['case'], r['host'], r['model'], r['effort']) for r in other)
    for k, v in sorted(c.items(), key=lambda x: str(x)):
        L.append('%4d  %s' % (v, ' | '.join(str(x) for x in k)))
    L.append('')
    L.append('=== Per run ===')
    for r in sorted(runs, key=lambda r: (r['scope'], r['run_folder'])):
        o = r['open']
        L.append('')
        L.append('%s  [%s]' % (r['run_folder'], r['scope']))
        L.append('  case=%s host=%s model=%s effort=%s date=%s shiploop=%s' % (r['case'], r['host'], r['model'], r['effort'], r['date'], r['shiploop_version']))
        L.append('  categories apply %d/%d; questions %d; by route %s; later results %d; spec found %s' % (
            r['categories_apply'], r['categories_total'], r['n_questions'], r['by_route'], r['later_results'], r['has_spec']))
        if r['questions']:
            L.append('  referenced later (id / id+words): %d / %d of %d' % (
                sum(q['id_only'] for q in r['questions']), sum(q['id_plus_words'] for q in r['questions']), r['n_questions']))
            for q in r['questions']:
                L.append('    %s %s %-10s id=%s id+w=%s  %s' % (q['id'], q['category'], q['route'], 'Y' if q['id_only'] else '-',
                                                                'Y' if q['id_plus_words'] else '-', (q['question'] or '')[:110].replace('\n', ' ')))
        L.append('  open: struct_assumptions=%d struct_unverified=%d struct_awaiting=%d heading_entries real/none=%d/%d know_assum_lines=%d regex=%s negated~=%s' % (
            o['structured_assumptions_in_later_results'], o['structured_unverified_in_later_results'], o['structured_awaiting_in_later_results'],
            o['knowledge_open_heading_entries_real'], o['knowledge_open_heading_entries_none'], o['knowledge_lines_with_assum'], o['regex_line_counts'], o['negated_mention_lines_approx']))
    open(path, 'w').write('\n'.join(L).replace(ROOT + '/', '~/') + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
