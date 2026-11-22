import os, re, sys, json
ROOTS = ["ratchet-pilot-20261120-b6eab2","ratchet-lens-20261121-08805f","ratchet-reworded-20261121-08805f","ratchet-parallel-20261121-6f54fb"]
BASE = os.path.expanduser("~/e2e-runs")
EXT = (".js",".cjs",".mjs")
TITLE_FUNCS = r"(?:test|it|check|register|item|task|workspace|http|fixture|validation|scenario|apiCheck|rejectsRows|staticCheck|offprep|suite|describe|wireCursor)"
TITLE_RE = re.compile(r"^\s*(?:(?:await\s+)?(?:[\w$]+\.)*" + TITLE_FUNCS + r"(?:\.\w+)?\(\s*(['\"`])(.*?)\1|[\w$.]+\[\s*(['\"`])([A-Z]{1,2}-\d+)\3\s*\]\s*=|(['\"`])([A-Z]{1,2}-\d+)\5\s*:)")
ID_RE = re.compile(r"""['"`]([A-Z]{1,2}-\d+)\b""")

def suite_files(d):
    out = []
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if x != "node_modules"]
        for f in fn:
            if f.endswith(EXT):
                out.append(os.path.join(dp, f))
    return sorted(out)

def find_enclosing_calls(text, pos):
    """yield (start_of_args_paren, end) for calls enclosing pos from innermost outward"""
    res = []
    depth = 0
    i = pos
    stack = []
    # scan backward tracking parens, ignoring strings crudely
    j = pos
    d = 0
    while j >= 0:
        c = text[j]
        if c in ')]}':
            d += 1
        elif c in '([{':
            if d == 0:
                if c == '(':
                    res.append(j)
                # continue outward
            else:
                d -= 1
        j -= 1
    return res

def match_close(text, i):
    d = 0
    j = i
    q = None
    n = len(text)
    while j < n:
        c = text[j]
        if q:
            if c == '\\': j += 1
            elif c == q: q = None
        else:
            if c in '"\'`': q = c
            elif c == '(' : d += 1
            elif c == ')':
                d -= 1
                if d == 0: return j
        j += 1
    return n-1

T1 = re.compile(r"""(?<=['"`\s=,\[])--test(?![-\w])""")
T2 = re.compile(r"""['"`]test['"`]""")
SPAWN = re.compile(r"\b(spawnSync|spawn|execFileSync|execSync|execFile|exec)\s*\(")
NPMWORD = re.compile(r"\bnpm\b|npmTest|Npm\b|execPath|nodeRun|\bnode\b")

def line_of(text, pos):
    return text.count('\n', 0, pos) + 1

def call_name(text, paren):
    m = re.search(r"([\w$.]+)\s*$", text[max(0,paren-60):paren])
    return m.group(1) if m else ''

def find_sites(text):
    sites = {}
    for rx, kind in ((T1,'flag'),(T2,'testword')):
        for m in rx.finditer(text):
            calls = find_enclosing_calls(text, m.start())
            chosen = None
            for p in calls:
                name = call_name(text, p)
                end = match_close(text, p)
                body = text[p:end+1]
                if name in ('require','join','resolve','readFileSync','readdirSync','match','test','it','check','register','item','task','describe','scenario','assert','equal','ok','deepEqual','push','includes','startsWith','endsWith') :
                    continue
                if name.split('.')[-1] in ('join','resolve','readFileSync','readdirSync','mkdirSync','existsSync','statSync','relative','basename','filter','map','some','find','includes','startsWith','endsWith','push','match','equal','ok','deepEqual','strictEqual','rejects','throws','assert','test','it','check','register','item','task','workspace','http','fixture','scenario'):
                    continue
                if kind == 'testword':
                    # need npm context and 'test' as the first array/arg element
                    # must be first element: previous non-space char is [ or (
                    before = text[:m.start()].rstrip()
                    if before[-1:] not in '[(': continue
                    if not NPMWORD.search(body) and not re.search(r"npm", name, re.I): continue
                else:
                    pass
                chosen = (p, end, name)
                break
            if chosen:
                sites[chosen[0]] = (chosen[1], chosen[2], kind)
    return sites
