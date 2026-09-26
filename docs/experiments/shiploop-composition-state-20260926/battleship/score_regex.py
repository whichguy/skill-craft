"""Score Battleship outputs: which considerations each plan raises (regex, runtime-aware)."""
import json, re, sys, pathlib, collections
I = re.I
C = {
 "identity": {"GAS": r"getActiveUser|getEffectiveUser|USER_ACCESSING|executeAs|Session\.", "SF": r"UserInfo|User(Id| record)|Experience Cloud|\bguest\b|Profile|Permission Set", "CF": r"Cloudflare Access|OAuth|JWT|session (cookie|token)|passkey|magic link"},
 "storage":  {"GAS": r"PropertiesService|CacheService|SpreadsheetApp|Sheet|DriveApp|Firestore|ScriptProperties", "SF": r"__c\b|custom object|Platform Cache", "CF": r"Durable Object|\bKV\b|\bD1\b|\bR2\b"},
 "server_api": {"GAS": r"google\.script\.run|doPost", "SF": r"@AuraEnabled|@RestResource|Apex (controller|class|method)", "CF": r"fetch\(\) handler|fetch handler|/api/|route|endpoint"},
 "hidden_state": {"*": r"authoritative|never (be )?(sent|return|expos|reveal|leav)|not (be )?(sent|returned|exposed|revealed)|cheat|tamper|server[- ]side (validation|only)|redact"},
 "concurrency": {"GAS": r"LockService|concurren|race", "SF": r"FOR UPDATE|optimistic|record lock|concurren|race", "CF": r"single[- ]threaded|serializ|transaction|concurren|race|optimistic"},
 "notify": {"*": r"\bpoll|Platform Event|empApi|Streaming API|WebSocket|\bpush\b|CometD|Change Data Capture|setInterval|refreshApex|server-sent|\bSSE\b"},
 "lifecycle": {"*": r"expir|\bTTL\b|clean ?up|abandon|timeout|purge|retention|delete (old|stale|finished|completed)"},
 "quotas": {"*": r"quota|governor|limits?\b"},
 "info_lifecycle": {"*": r"\bPII\b|personal (data|information)|privacy|email address|retain|retention"},
}
def text_of(f):
    if f.suffix == ".md": return f.read_text(), None
    res, reads = "", []
    for line in f.read_text().splitlines():
        try: e = json.loads(line)
        except Exception: continue
        if e.get("type") == "result": res = e.get("result", "")
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use": reads.append(c["input"].get("file_path") or c["input"].get("pattern"))
    return res, reads
def score(t, rt):
    return {k: bool(re.search(v.get(rt, v.get("*")), t, I)) for k, v in C.items()}
if __name__ == "__main__":
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    rows = collections.defaultdict(list); reads_log = collections.defaultdict(list)
    for f in sorted(outdir.glob("*_*_*_[0-9].*")):
        if f.suffix not in (".md", ".jsonl"): continue
        rt, req, var, k = f.stem.split("_")
        t, reads = text_of(f)
        if not t.strip(): print("EMPTY", f.name); continue
        rows[(rt, req, var)].append(score(t, rt))
        if reads is not None: reads_log[(rt, req, var)].append(len([r for r in reads if r and "references" in str(r)]))
    keys = list(C)
    print(f"{'cell':32}" + " ".join(k[:8].rjust(8) for k in keys) + "  total")
    for cell in sorted(rows, key=lambda c: (c[1], c[0], c[2])):
        rs = rows[cell]; n = len(rs)
        cnt = [sum(r[k] for r in rs) for k in keys]
        tot = sum(cnt) / n
        extra = f"  guide-reads={reads_log[cell]}" if cell in reads_log else ""
        print(f"{'/'.join(cell):32}" + " ".join(f"{c}/{n}".rjust(8) for c in cnt) + f"  {tot:4.1f}{extra}")
