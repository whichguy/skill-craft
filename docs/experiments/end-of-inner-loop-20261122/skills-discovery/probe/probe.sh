#!/bin/bash
# Codex project-skill discovery probe (no model call): `codex debug prompt-input` renders the
# model-visible input of a new session. Everything it builds lives under $ROOT; Codex runs with a
# throwaway HOME and CODEX_HOME inside $ROOT, so it writes nothing to the real profile.
# Re-run from scratch: bash probe.sh   (it deletes and rebuilds only $ROOT/work, $ROOT/out, $ROOT/home, $ROOT/codex-home)
set -euo pipefail
ROOT=/Users/dadleet/src/skill-craft/docs/experiments/end-of-inner-loop-20261122/skills-discovery/probe
: "${ROOT:?}"
WORK="$ROOT/work"; OUT="$ROOT/out"
rm -rf "${WORK:?}" "${OUT:?}" "${ROOT:?}/home" "${ROOT:?}/codex-home"
mkdir -p "$WORK" "$OUT" "$ROOT/home" "$ROOT/codex-home"

skill() {  # skill <dir> <name>: a minimal SKILL.md
  mkdir -p "$1"
  printf -- '---\nname: %s\ndescription: Probe skill %s for the discovery test.\n---\n\n# %s\n\nProbe body.\n' "$2" "$2" "$2" > "$1/SKILL.md"
}
commit() { git -C "$1" add -A && git -C "$1" -c user.name=probe -c user.email=probe@example.invalid commit -q -m "$2"; }

# Repo A: the main checkout. Each candidate location holds one uniquely named skill.
A="$WORK/a"; mkdir -p "$A"; git -C "$A" init -q -b main
skill "$A/.agents/skills/probe-agents-real"            probe-agents-real        # documented REPO root, real folder
skill "$A/shiploop-skills/probe-linked-skill"           probe-linked-skill       # the named folder ShipLoop would own
ln -s ../../shiploop-skills/probe-linked-skill "$A/.agents/skills/probe-linked-skill"   # relative per-skill symlink
skill "$WORK/outside/probe-abs-target"                  probe-abs-link           # a folder outside the repository
ln -s "$WORK/outside/probe-abs-target" "$A/.agents/skills/probe-abs-link"         # absolute per-skill symlink
skill "$A/.codex/skills/probe-codex-dir"                probe-codex-dir          # legacy project .codex/skills
skill "$A/.claude/skills/probe-claude-dir"              probe-claude-dir         # Claude Code's project folder
skill "$A/skills/probe-plain"                           probe-plain              # ShipLoop's default skills/<name>
skill "$A/sub/.agents/skills/probe-sub"                 probe-sub                # nested below the root
printf '# Probe repo\n\nRepository skills live in `shiploop-skills/` (index: shiploop-skills/INDEX.md). Read the index before planning.\n' > "$A/AGENTS.md"
commit "$A" "probe repo A"

# Repo B: the whole .agents/skills directory is one symlink to the named folder.
B="$WORK/b"; mkdir -p "$B/.agents"; git -C "$B" init -q -b main
skill "$B/shiploop-skills/probe-dirlink" probe-dirlink
ln -s ../shiploop-skills "$B/.agents/skills"
commit "$B" "probe repo B"

# A linked worktree placed the way ShipLoop places its own: <parent>/.shiploop-runs/<repo>-<stamp>/worktree.
WT="$WORK/.shiploop-runs/a-probe/worktree"
mkdir -p "$(dirname "$WT")"
git -C "$A" worktree add -q "$WT" -b probe-wt

render() {  # render <label> <cwd> [codex -c args...]
  local label="$1" cwd="$2" rc=0; shift 2
  ( cd "$cwd" && env -i PATH="/opt/homebrew/bin:/usr/bin:/bin" HOME="$ROOT/home" CODEX_HOME="$ROOT/codex-home" TERM=dumb \
      codex debug prompt-input "$@" "hello" ) > "$OUT/$label.json" 2> "$OUT/$label.stderr" || rc=$?
  echo "== $label (cwd ${cwd#"$WORK"/}) exit=$rc" >> "$OUT/summary.txt"
  python3 -I "$ROOT/extract.py" "$OUT/$label.json" >> "$OUT/summary.txt"
}

render 00-baseline-no-repo-skills "$WORK/outside"
render 01-main-root      "$A"
render 02-main-sub       "$A/sub"
render 03-dirlink        "$B"
render 04-wt-committed   "$WT"
skill "$WT/.agents/skills/probe-wt-new" probe-wt-new          # created in the worktree mid-run, uncommitted
skill "$A/.agents/skills/probe-main-new" probe-main-new       # created in the main checkout, uncommitted
render 05-main-after-wt-skill "$A"
render 06-wt-after-wt-skill   "$WT"
render 07-enable-by-path  "$A" -c "skills.config=[{path=\"$A/skills/probe-plain/SKILL.md\",enabled=true}]"

# Repo C: does Codex read through to the main checkout's skills when the worktree has none (Claude Code v2.1.277+
# does, per its worktree docs)? The main checkout's .agents/skills is untracked, so the worktree has no copy.
C="$WORK/c"; mkdir -p "$C"; git -C "$C" init -q -b main
printf '# Probe repo C\n' > "$C/README.md"
commit "$C" "probe repo C"
skill "$C/.agents/skills/probe-c-main-untracked" probe-c-main-untracked
WTC="$WORK/.shiploop-runs/c-probe/worktree"
mkdir -p "$(dirname "$WTC")"
git -C "$C" worktree add -q "$WTC" -b probe-wt-c
render 10-c-main-untracked "$C"
render 11-c-wt-no-skills-dir "$WTC"

# Side check of a recorded note (memory use-the-codex-harness, 2026-11-20: "lists every skill under the account's
# real home whatever HOME and CODEX_HOME say"): the same render with the real HOME (read only) and the throwaway
# CODEX_HOME. If user scope follows $HOME, ~/.agents/skills appears here and in no render above.
rc=0
( cd "$A" && env -i PATH="/opt/homebrew/bin:/usr/bin:/bin" HOME="/Users/dadleet" CODEX_HOME="$ROOT/codex-home" TERM=dumb \
    codex debug prompt-input "hello" ) > "$OUT/08-real-home.json" 2> "$OUT/08-real-home.stderr" || rc=$?
echo "== 08-real-home (cwd a, HOME=/Users/dadleet, CODEX_HOME throwaway) exit=$rc" >> "$OUT/summary.txt"
python3 -I "$ROOT/extract.py" "$OUT/08-real-home.json" >> "$OUT/summary.txt"

# Codex's skill-related feature flags, defaults only (the throwaway CODEX_HOME holds no config).
( cd "$WORK/outside" && env -i PATH="/opt/homebrew/bin:/usr/bin:/bin" HOME="$ROOT/home" CODEX_HOME="$ROOT/codex-home" TERM=dumb \
    codex features list ) 2>&1 | grep -i -E "skill|world_state|catalog" > "$OUT/09-features-default.txt" || true
codex --version > "$OUT/codex-version.txt" 2>&1 || true

# Keep compact evidence: the skills block (and one AGENTS.md block) of each render, the summary and the flags.
python3 -I - "$OUT" <<'EOF'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
for path in sorted(out.glob("*.json")):
    texts = [part["text"] for item in json.load(open(path, encoding="utf-8")) for part in (item.get("content") or [])
             if isinstance(part, dict) and isinstance(part.get("text"), str)]
    block = next((t for t in texts if t.startswith("<skills_instructions>")), "(no skills block)")
    (out / (path.stem + ".skills-block.txt")).write_text(block + "\n", encoding="utf-8")
    if path.stem == "01-main-root":
        agents = next((t for t in texts if t.startswith("# AGENTS.md instructions for")), "(no AGENTS.md block)")
        (out / (path.stem + ".agents-md-block.txt")).write_text(agents + "\n", encoding="utf-8")
EOF
if [ "${KEEP_SCAFFOLD:-0}" != "1" ]; then
  # The full renders (about 76 KB each, mostly Codex's own base instructions), the empty stderr files, the probe
  # repositories (nested Git repositories inside skill-craft) and the throwaway profile are not kept.
  rm -f "$OUT"/*.json
  find "$OUT" -name '*.stderr' -size 0 -delete
  git -C "$A" worktree remove --force "$WT"; git -C "$C" worktree remove --force "$WTC"
  rm -rf "${WORK:?}" "${ROOT:?}/home" "${ROOT:?}/codex-home"
fi
echo "done; summary in $OUT/summary.txt"
