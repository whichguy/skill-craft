#!/bin/sh
# Clean-install probes for the published skill-craft plugin (no model).
# Usage: probes.sh SCRATCH_DIR     (must not exist; the script creates it and a disposable Claude config inside it)
# Needs: claude CLI, git, network access to github.com/whichguy/skill-craft, /usr/bin/python3 (any 3.9+); docker is optional.
set -u
S=${1:?scratch dir}; [ -e "$S" ] && { echo "refusing: $S exists" >&2; exit 2; }
mkdir -p "$S" && cd "$S" || exit 2
D=$S/claude-config; mkdir -p "$D"; export CLAUDE_CONFIG_DIR="$D"
echo "## install into a disposable config"
claude plugin marketplace add whichguy/skill-craft 2>&1 | tail -1
claude plugin install skill-craft@whichguy 2>&1 | tail -1
claude plugin list --json | python3 -c 'import json,sys; [print(p["id"], p["version"], "enabled" if p.get("enabled") else "disabled") for p in json.load(sys.stdin)]'
V=$(ls "$D/plugins/cache/whichguy/skill-craft"); P=$D/plugins/cache/whichguy/skill-craft/$V; E=$P/skills/shiploop/scripts
echo "## installed tree vs the published tree (git archive of origin/main plugins/skill-craft); no output = identical"
rm -rf "$S/pub" && mkdir "$S/pub" && git -C "${SKILL_CRAFT_CHECKOUT:-$HOME/src/skill-craft}" archive origin/main plugins/skill-craft | tar -x -C "$S/pub"
diff -rq "$S/pub/plugins/skill-craft" "$P" | grep -v -E '__pycache__|\.in_use|\.git$'
echo "## entry modes"
for f in shiploop shiploop-drive shiploop-hook shiploop-keepalive-observe shiploop-keepalive-stop shiploop-keepalive-session-end shiploop-skill-call shiploop-status-hook; do printf '%s %s\n' "$(ls -l "$E/$f" | cut -c1-10)" "$f"; done
grep -n 'FLOOR =' "$E/shiploop_pyfloor.py"
grep -o 'needs `python3` 3.9 or newer and `git` on PATH' "$P/skills/shiploop/SKILL.md" | head -1
echo "## stock Python, clean environment (env -i)"
T=$S/repo; mkdir -p "$T/home" && git init -q "$T" && git -C "$T" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
run() { env -i HOME="$T/home" PATH=/usr/bin:/bin:/usr/sbin:/sbin PYTHONDONTWRITEBYTECODE=1 "$@"; }
echo "python: $(run /usr/bin/python3 --version 2>&1)"
run /usr/bin/python3 "$E/shiploop" --help >/dev/null 2>&1; echo "shiploop --help exit=$?"
OUT=$(run /usr/bin/python3 "$E/shiploop" workspace start --repo "$T" --prompt "Create hello.py that prints Hello, world!" 2>&1); echo "workspace start exit=$? packet_bytes=$(printf '%s' "$OUT" | wc -c | tr -d ' ')"
echo "## hooks with python3 absent from PATH (coreutils only)"
B=$S/nopython; mkdir "$B"; for t in cat dirname sh grep tr head env sed; do ln -s "$(command -v $t)" "$B/$t"; done
for e in shiploop-keepalive-observe shiploop-keepalive-stop shiploop-keepalive-session-end shiploop-skill-call shiploop-status-hook; do o=$(echo '{}' | env -i HOME="$T/home" PATH="$B" /bin/sh "$E/$e" 2>&1); echo "$e exit=$? out=[$o]"; done
echo "## Python 3.7.3 (node:14 image) with the installed tree"
if docker info >/dev/null 2>&1; then
  docker run --rm -v "$P":/plug:ro node:14 sh -c 'python3 --version; for e in shiploop-keepalive-observe shiploop-keepalive-stop shiploop-keepalive-session-end shiploop-skill-call shiploop-status-hook; do o=$(echo "{}" | /plug/skills/shiploop/scripts/$e 2>&1); echo "$e exit=$? out=[$o]"; done; python3 /plug/skills/shiploop/scripts/shiploop --help; echo "shiploop --help exit=$?"; echo "{}" | python3 /plug/skills/shiploop/scripts/shiploop-hook observe --host auto; echo "shiploop-hook observe exit=$?"' 2>&1
else echo "docker not running: skipped"; fi
