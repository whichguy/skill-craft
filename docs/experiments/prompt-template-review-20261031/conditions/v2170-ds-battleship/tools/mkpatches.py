import subprocess, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variants import V
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work')
PATCHES = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship/patches'
def git(*a): return subprocess.run(['git', '-C', WORK, *a], capture_output=True, text=True)
def reset(): git('checkout', '--', '.'); git('clean', '-fdq')
SPECIAL_725 = None
def apply(vid, edits):
    for e in edits:
        f = os.path.join(WORK, e[0])
        s = open(f).read()
        if len(e) == 4 and e[3] == 'special':
            # R-7.25: drop the try/catch around createGame
            a = s.index("      let game;\n      try {\n        game = createGame({ random });")
            b = s.index("      games.set(id, game);")
            s = s[:a] + "      const game = createGame({ random });\n" + s[b:]
        else:
            n = s.count(e[1])
            if n != 1:
                raise SystemExit(f'{vid}: {e[0]}: expected 1 match, found {n} for {e[1][:70]!r}')
            s = s.replace(e[1], e[2])
        open(f, 'w').write(s)
only = sys.argv[1:]
reset()
for vid, edits in V.items():
    if only and vid not in only: continue
    apply(vid, edits)
    d = git('diff').stdout
    assert d.strip(), vid
    open(os.path.join(PATCHES, vid + '.patch'), 'w').write(d)
    # syntax check
    for f in set(e[0] for e in edits):
        if f.endswith('.js'):
            r = subprocess.run(['node', '--check', os.path.join(WORK, f)], capture_output=True, text=True)
            if r.returncode: print(vid, 'SYNTAX', r.stderr[:300])
    reset()
print('patches:', len(os.listdir(PATCHES)))
