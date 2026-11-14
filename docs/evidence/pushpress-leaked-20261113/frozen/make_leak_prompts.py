#!/usr/bin/env python3
"""Check the author agent's batch against prompts/author-brief.md and write the harness file prompts/leak-prompts.json.

usage: make_leak_prompts.py <leak-agent-output.json> <leak-prompts.json>

Exit status 1, and no output file, when the batch breaks the brief: counts or classes, a leak prompt without PushPress, a quiet prompt with it, fewer than six leak
prompts without the word leak/leaked/leaking, a duplicate text, a very long text or an id out of sequence. The texts are copied verbatim.
"""
import json
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src))
pos, neg = d["positives"], d["negatives"]
problems = []


def norm(t):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t.lower()).split())


if [x["id"] for x in pos] != [f"LP{i}" for i in range(1, 13)]:
    problems.append("positive ids are not LP1..LP12 in order")
if [x["id"] for x in neg] != [f"LN{i}" for i in range(1, 13)]:
    problems.append("negative ids are not LN1..LN12 in order")
cls = [x.get("class") for x in pos]
if cls.count("code") != 6 or cls.count("people") != 6 or len(cls) != 12:
    problems.append(f"positive classes: {cls.count('code')} code, {cls.count('people')} people, {len(cls)} in all (want 6, 6, 12)")
kinds = [x.get("kind") for x in neg]
if (kinds.count("other-product"), kinds.count("no-product"), kinds.count("not-a-key"), len(kinds)) != (8, 2, 2, 12):
    problems.append(f"negative kinds: {kinds.count('other-product')} other-product, {kinds.count('no-product')} no-product, {kinds.count('not-a-key')} not-a-key (want 8, 2, 2)")
for x in pos:
    if "pushpress" not in x["text"].lower():
        problems.append(f"{x['id']} does not name PushPress")
for x in neg:
    if "pushpress" in x["text"].lower():
        problems.append(f"{x['id']} names PushPress")
without_leak = sum(1 for x in pos if not re.search(r"leak", x["text"], re.I))
if without_leak < 6:
    problems.append(f"only {without_leak} leak prompts avoid the word leak (want at least 6)")
seen = {}
for x in pos + neg:
    k = norm(x["text"])
    if k in seen:
        problems.append(f"{x['id']} duplicates {seen[k]}")
    seen[k] = x["id"]
    if len(x["text"]) > 1200 or not x["text"].strip():
        problems.append(f"{x['id']} is empty or longer than 1200 characters")
longtok = [x["id"] for x in pos + neg if re.search(r"[A-Za-z0-9_\-]{28,}", x["text"])]

print(f"positives {len(pos)} (code {cls.count('code')}, people {cls.count('people')}); without the word leak: {without_leak}; negatives {len(neg)} {dict((k, kinds.count(k)) for k in sorted(set(kinds)))}")
print("long token-like strings in:", longtok or "none")
if problems:
    print("BATCH BREAKS THE BRIEF:")
    for p_ in problems:
        print("  -", p_)
    sys.exit(1)

prompts = [dict(id=x["id"], category=f"leak-{x['class']}", expect_fire=True, text=x["text"]) for x in pos] + \
          [dict(id=x["id"], category=f"neg-{x['kind']}", expect_fire=False, text=x["text"]) for x in neg]
json.dump(dict(version=1, purpose="P25 held-out set: leaked-key prompts that should load the card (LP) and quiet prompts that should not (LN), as the fresh author agent wrote them (verbatim); see author-brief.md.",
               source=src.split("/")[-1], prompts=prompts), open(dst, "w"), indent=1)
print("wrote", dst, len(prompts), "prompts")
