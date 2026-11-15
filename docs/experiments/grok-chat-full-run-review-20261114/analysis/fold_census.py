import sys, os, re, json, glob, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "skills", "shiploop", "scripts"))
import shiploop_test_loop as tl
FIELDS = ("test_commands", "system_commands")
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
runs = set(); subs = 0; subs_with_fold = 0
rows_in = rows_out = 0
nonadj_check = []      # (run, field, command, positions)
any_fold_runs = set(); nonadj_runs = set()
bad = 0
for tf in files:
    rd = os.path.dirname(tf)
    ib = os.path.join(rd, "inbox")
    if not os.path.isdir(ib): continue
    for p in glob.glob(os.path.join(ib, "nav-*.md")):
        try: t = open(p, errors="replace").read()
        except Exception: continue
        m = re.search(r"```shiploop-state\n(.*?)\n```", t, re.S)
        if not m: continue
        try: o = json.loads(m.group(1))
        except Exception: continue
        for field in FIELDS:
            raw = o.get(field)
            if not isinstance(raw, list) or not raw: continue
            subs += 1; runs.add(tf)
            try: norm = tl.normalise_commands(raw)
            except Exception: bad += 1; continue
            rows_in += len(raw); rows_out += len(norm)
            if len(norm) < len(raw):
                subs_with_fold += 1; any_fold_runs.add(tf)
            seen = collections.defaultdict(list)
            for i, r in enumerate(raw):
                if isinstance(r, dict) and r.get("suite") == "check":
                    seen[r.get("command", "").strip()].append(i)
            for cmd, pos in seen.items():
                if len(pos) > 1 and any(pos[i + 1] - pos[i] > 1 for i in range(len(pos) - 1)):
                    nonadj_check.append((tf, field, cmd, pos, len(raw))); nonadj_runs.add(tf)
print("runs with raw command submissions:", len(runs), " submissions:", subs, " (unreadable by current normaliser:", bad, ")")
print("rows submitted:", rows_in, "-> accepted:", rows_out, " rows folded:", rows_in - rows_out, " in", subs_with_fold, "submissions /", len(any_fold_runs), "runs")
print("NON-ADJACENT repeated 'check' rows (same command string, other rows between):", len(nonadj_check), "submissions in", len(nonadj_runs), "runs")
for tf, field, cmd, pos, n in nonadj_check[:14]:
    short = tf.replace("/Users/dadleet/", "~/").split("/.shiploop-runs")[0][-60:]
    print(f"   ..{short} {field} rows {pos} of {n}: {cmd[:88]}")
