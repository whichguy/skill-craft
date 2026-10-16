"""Resolve every file reference on every Technique Atlas card against live GitHub trees.

Reads  export/techniques/*.json (card docs) and trees/*.json (gh git trees).
Writes refpatch/<id>.json   {"refs": [...]}   and refreport.txt (what could not be resolved).
"""
import json, glob, os, re, sys, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
trees = {}
for f in glob.glob(os.path.join(BASE, "trees", "*.json")):
    repo = os.path.basename(f)[:-5].replace("_", "/", 1)
    j = json.load(open(f))
    trees[repo] = [t["path"] for t in j["tree"] if t["type"] == "blob"]
# repos whose names contain "_" (asgeirtj/system_prompts_leaks) lose the right split; fix explicitly
for k in list(trees):
    pass
trees["asgeirtj/system_prompts_leaks"] = trees.pop("asgeirtj/system/prompts/leaks", trees.get("asgeirtj/system_prompts_leaks", []))

REPO_ALIASES = {"ecc": "affaan-m/ECC", "superpowers": "obra/superpowers", "ralph": "snarktank/ralph",
                "spec-kit": "github/spec-kit", "openspec": "Fission-AI/OpenSpec", "bmad": "bmad-code-org/BMAD-METHOD",
                "gsd": "gsd-build/get-shit-done", "codex": "openai/codex", "aider": "Aider-AI/aider",
                "repowise": "repowise-dev/claude-code-prompts", "claude-code": "anthropics/claude-code"}
KNOWN = set(trees)

def gh(repo, path):
    return "https://github.com/%s/blob/HEAD/%s" % (repo, urllib.parse.quote(path))

def resolve(repo, path):
    """Return (resolved_path, how) or (None, None) inside repo's tree."""
    files = trees.get(repo)
    if files is None:
        return None, None
    if path in files:
        return path, "exact"
    base = os.path.basename(path)
    cands = [f for f in files if os.path.basename(f) == base]
    if not cands:
        cands = [f for f in files if os.path.basename(f).lower() == base.lower()]
    if len(cands) == 1:
        return cands[0], "basename"
    if cands:  # prefer longest shared suffix
        def score(f):
            a, b = f.split("/")[::-1], path.split("/")[::-1]
            n = 0
            for x, y in zip(a, b):
                if x != y: break
                n += 1
            return n
        cands.sort(key=score, reverse=True)
        if score(cands[0]) > 1:
            return cands[0], "suffix"
    # directory prefix (e.g. "skills/ralph/")
    p = path.rstrip("/")
    if any(f.startswith(p + "/") for f in files):
        return p, "dir"
    return None, None

NAMEPART = {r.split("/")[1].lower(): r for r in KNOWN}
NAMEPART.update({k: v for k, v in REPO_ALIASES.items()})
NAMEPART["bmad-method"] = "bmad-code-org/BMAD-METHOD"

def clean(s):
    s = re.sub(r"\blines?\s*~?\d+(\s*-\s*\d+)?", " ", s)
    s = re.sub(r"\b(step|INSTRUCTIONS)\s*\d+", " ", s)
    s = re.sub(r"\s\+\s", ", ", s)
    return s

def split_candidates(s):
    s = clean(s)
    s = re.sub(r"\([^)]*\)", " ", s)          # drop parenthetical notes
    parts = re.split(r"[;,]|\s{2,}|\s+and\s+", s)
    out = []
    for p in parts:
        p = p.strip().strip("`'\" .")
        if not p:
            continue
        p = re.sub(r"\(\)$", "", p)
        out.append(p)
    return out

def looks_like_path(p):
    return ("/" in p or re.search(r"\.[A-Za-z0-9]{1,5}$", p)) and not p.startswith("http")

def main():
    report = []
    for f in sorted(glob.glob(os.path.join(BASE, "export", "techniques", "*.json"))):
        doc = json.load(open(f))
        cid = os.path.basename(f)[:-5]
        card_repos = [r for r in doc.get("repos", []) if r in KNOWN]
        det = doc.get("detail") or {}
        for s in det.get("sources", []):
            if s.get("repo") in KNOWN and s["repo"] not in card_repos:
                card_repos.append(s["repo"])
        refs, seen = [], set()

        def add(repo, path, label=None, why=None):
            key = (repo, path)
            if key in seen: return
            seen.add(key)
            rp, how = resolve(repo, path)
            if rp:
                refs.append({"repo": repo, "path": rp, "url": gh(repo, rp), "kind": "file", "verified": True, "how": how})
            else:
                q = urllib.parse.quote_plus("repo:%s path:%s" % (repo, os.path.basename(path)))
                refs.append({"repo": repo, "path": path, "url": "https://github.com/search?q=%s&type=code" % q,
                             "kind": "search", "verified": False})
                report.append("%s: NOT FOUND %s :: %s" % (cid, repo, path))

        def handle(raw, repo_hint=None):
            raw = re.sub(r"(?<![/\w.])((?:swebench\.com|anthropic\.com|code\.claude\.com)/[^\s,;)\]]+)", r"https://\1", raw)
            for u in re.findall(r"https?://[^\s,;)\]]+", raw):
                u = u.rstrip(".")
                if (u, "") not in seen:
                    seen.add((u, ""))
                    refs.append({"repo": urllib.parse.urlparse(u).netloc, "path": urllib.parse.urlparse(u).path or "/",
                                 "url": u, "kind": "web", "verified": None})
            raw2 = re.sub(r"https?://[^\s,;)\]]+", " ", raw)
            lead = re.match(r"\s*([A-Za-z0-9_.\-]+)\s+(\S.*)$", raw2)
            if lead and lead.group(1).lower() in NAMEPART and "/" not in lead.group(1):
                repo_hint = NAMEPART[lead.group(1).lower()]; raw2 = lead.group(2)
            # explicit "owner/name " prefix
            m = re.match(r"\s*([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)\s+(.*)$", raw2)
            hint = repo_hint
            if m and m.group(1) in KNOWN:
                hint, raw2 = m.group(1), m.group(2)
            # "(short-name)" alias
            alias = re.search(r"\(([A-Za-z\-/ ]+)\)", raw)
            if alias and alias.group(1).strip().lower() in REPO_ALIASES:
                hint = REPO_ALIASES[alias.group(1).strip().lower()]
            for c0 in split_candidates(raw2):
                if "*" in c0: continue
                if c0.startswith("/") and c0.count("/") >= 1 and "." not in c0.split("/")[-1]:
                    u = "https://platform.claude.com/docs/en" + c0
                    if (u, "") not in seen:
                        seen.add((u, "")); refs.append({"repo": "platform.claude.com", "path": "/docs/en" + c0, "url": u, "kind": "web", "verified": None})
                    continue
                repos_try = ([hint] if hint else []) + [r for r in card_repos if r != hint]
                done = False
                for r in repos_try + [k for k in KNOWN if k not in repos_try]:
                    rp, how = resolve(r, c0)
                    if rp and (how == "exact" or (r in repos_try and how in ("basename", "suffix"))):
                        add(r, c0); done = True; break
                if done: continue
                toks = [t.strip("`'\".:") for t in c0.split()] if " " in c0 else [c0]
                toks = [t for t in toks if looks_like_path(t)]
                if not toks: continue
                for t in toks:
                    for r in repos_try:
                        rp, _ = resolve(r, t)
                        if rp:
                            add(r, t); done = True; break
                    if done: break
                if not done and repos_try and ("/" in toks[0] or toks[0].endswith((".md",".py",".ts",".js",".sh",".yaml",".yml",".json",".rs",".txt",".toml"))):
                    add(repos_try[0], toks[0])

        for e in doc.get("evidence", []):
            handle(e)
        for s in det.get("sources", []):
            r = s.get("repo")
            if r in KNOWN: handle(s.get("path", ""), r)
            elif r and "." in r and "/" not in r and not s.get("path","").startswith("http"):
                pth = re.split(r"\s+\(|\s{2,}", s.get("path",""))[0].strip()
                u = "https://%s/%s" % (r, pth)
                if (u, "") not in seen:
                    seen.add((u, "")); refs.append({"repo": r, "path": "/" + pth, "url": u, "kind": "web", "verified": None})
            else: handle(s.get("path", ""))
        for ex in det.get("examples", []):
            if ex.get("source") and ex["source"] != "illustrative": handle(ex["source"])
        # repo links themselves
        for r in doc.get("repos", []):
            if r in KNOWN and (r, "") not in seen:
                refs.insert(0, {"repo": r, "path": "", "url": "https://github.com/" + r, "kind": "repo", "verified": True})
                seen.add((r, ""))
        os.makedirs(os.path.join(BASE, "refpatch"), exist_ok=True)
        json.dump({"refs": refs}, open(os.path.join(BASE, "refpatch", cid + ".json"), "w"))
        files = [x for x in refs if x["kind"] == "file"]
        print(cid, len(refs), "file refs:", len(files), "unverified:", sum(1 for x in refs if x["kind"] == "search"))
    open(os.path.join(BASE, "refreport.txt"), "w").write("\n".join(report))
    print("unresolved:", len(report))

main()
