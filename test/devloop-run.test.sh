#!/usr/bin/env bash
# devloop-run preflight + bootstrap (hermetic where possible).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
run="$root/skills/devloop-run/scripts/devloop-run"
fixture_tgz="$root/test/fixtures/devloop-engine-fixture.tar.gz"
fixture_pin="$root/test/fixtures/engine-pin-fixture.json"

fail() {
  printf 'devloop-run.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$run" ]] || fail "scripts/devloop-run not executable"
[[ -f "$root/skills/devloop-run/SKILL.md" ]] || fail "missing SKILL.md"
[[ -f "$root/skills/devloop-run/references/bootstrap.md" ]] || fail "missing bootstrap.md"
[[ -f "$root/skills/devloop-run/references/engine-pin.json" ]] || fail "missing engine-pin.json"
[[ -f "$fixture_tgz" ]] || fail "missing fixture tgz"
python3 -c 'import json;d=json.load(open("'"$root"'/skills/devloop-run/references/engine-pin.json")); assert "version" in d and "url" in d and "sha256" in d' \
  || fail "engine-pin.json schema"

# Refresh fixture pin absolute path + sha
python3 - "$fixture_tgz" "$fixture_pin" <<'PY'
import hashlib, json, pathlib, sys
tgz, pin = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sha = hashlib.sha256(tgz.read_bytes()).hexdigest()
pin.write_text(json.dumps({"version": "fixture", "url": f"file://{tgz.resolve()}", "sha256": sha}, indent=2) + "\n")
PY

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/devloop-run-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

# D1: --help
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_DATA_HOME DEVLOOP_ENGINE_PIN DEVLOOP_ENGINE_SHA256 || true
export HOME="$tmpdir/empty-home"
mkdir -p "$HOME"
set +e
out1="$("$run" --help 2>&1)"
rc1=$?
set -e
[[ "$rc1" -eq 0 ]] || fail "D1 --help should exit 0 (got $rc1): $out1"
printf '%s\n' "$out1" | grep -q 'Truth table\|--setup\|Resolve order\|bootstrap' || true

# D1b: no engine + --no-bootstrap → exit 2
set +e
out1b="$("$run" --no-bootstrap "noop" 2>&1)"
rc1b=$?
set -e
[[ "$rc1b" -eq 2 ]] || fail "D1b want exit 2 got $rc1b: $out1b"

# D2: DEVLOOP_HOME fake engine
eng="$tmpdir/fake-engine"
mkdir -p "$eng/scripts"
cat >"$eng/scripts/devloop_cli.py" <<'PY'
import sys
print("STUB_CLI", " ".join(sys.argv[1:]))
sys.exit(0)
PY
export DEVLOOP_HOME="$eng"
out2="$("$run" -- hello --repo /tmp/x 2>&1)" || fail "D2: $out2"
printf '%s\n' "$out2" | grep -q 'STUB_CLI hello --repo /tmp/x' || fail "D2 stub: $out2"

# D3: strict invalid DEVLOOP_HOME
export DEVLOOP_HOME="$tmpdir/not-an-engine"
mkdir -p "$DEVLOOP_HOME"
set +e
out3="$("$run" --strict --no-bootstrap hi 2>&1)"
rc3=$?
set -e
[[ "$rc3" -eq 2 ]] || fail "D3 want 2 got $rc3: $out3"

# D4: frontmatter / honesty
grep -q 'kind: script-backed' "$root/skills/devloop-run/SKILL.md" || fail "D4 kind"
grep -qi 'bootstrap' "$root/skills/devloop-run/SKILL.md" || fail "D4 bootstrap"
grep -q 'Truth table' "$root/skills/devloop-run/SKILL.md" || fail "D4 truth table"

# D5: no bare skills/devloop
[[ ! -d "$root/skills/devloop" ]] || fail "D5 bare skills/devloop"

# D6: probe
export DEVLOOP_HOME="$eng"
out6="$("$run" --probe 2>&1)" || fail "D6: $out6"
printf '%s\n' "$out6" | grep -q 'engine=' || fail "D6: $out6"

# D7: strict broken home
export DEVLOOP_HOME="$tmpdir/not-an-engine"
mkdir -p "$HOME/.hermes/skills/software-development/devloop/scripts"
printf 'print(1)\n' >"$HOME/.hermes/skills/software-development/devloop/scripts/devloop_cli.py"
set +e
out7="$("$run" --strict --no-bootstrap hi 2>&1)"
rc7=$?
set -e
[[ "$rc7" -eq 2 ]] || fail "D7 want 2 got $rc7"

# D8: pin bootstrap (file:// fixture, no Hermes)
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL || true
rm -rf "$HOME/.hermes"
export DEVLOOP_DATA_HOME="$tmpdir/data"
export DEVLOOP_ENGINE_PIN="$fixture_pin"
out8="$("$run" --setup 2>&1)" || fail "D8 setup: $out8"
[[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D8 missing cli: $out8"
[[ -f "$DEVLOOP_DATA_HOME/devloop/.skill-craft-engine.json" ]] || fail "D8 missing marker"
out8p="$("$run" --probe --no-bootstrap 2>&1)" || fail "D8 probe: $out8p"
out8r="$("$run" -- hi 2>&1)" || fail "D8 run: $out8r"
printf '%s\n' "$out8r" | grep -q 'FIXTURE_ENGINE' || fail "D8 fixture run: $out8r"

# D9: sha mismatch fails closed
export DEVLOOP_DATA_HOME="$tmpdir/data-badsha"
python3 - "$fixture_tgz" "$tmpdir/bad-pin.json" <<'PY'
import hashlib, json, pathlib, sys
tgz = pathlib.Path(sys.argv[1]).resolve()
pathlib.Path(sys.argv[2]).write_text(json.dumps({
  "version": "x", "url": f"file://{tgz}", "sha256": "0" * 64
}, indent=2) + "\n")
PY
export DEVLOOP_ENGINE_PIN="$tmpdir/bad-pin.json"
set +e
out9="$("$run" --setup 2>&1)"
rc9=$?
set -e
[[ "$rc9" -eq 2 ]] || fail "D9 want 2 got $rc9: $out9"
printf '%s\n' "$out9" | grep -qi 'sha256 mismatch' || fail "D9 message: $out9"
[[ ! -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D9 partial install"

# D10: tarbomb refused
export DEVLOOP_DATA_HOME="$tmpdir/data-bomb"
python3 - "$tmpdir" <<'PY'
import tarfile, hashlib, json, pathlib, sys
td = pathlib.Path(sys.argv[1])
bomb = td / "bomb.tgz"
with tarfile.open(bomb, "w:gz") as tf:
    import io
    data = b"evil\n"
    info = tarfile.TarInfo(name="../evil.txt")
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))
sha = hashlib.sha256(bomb.read_bytes()).hexdigest()
(td / "bomb-pin.json").write_text(json.dumps({
  "version": "bomb", "url": f"file://{bomb.resolve()}", "sha256": sha
}, indent=2) + "\n")
PY
export DEVLOOP_ENGINE_PIN="$tmpdir/bomb-pin.json"
set +e
out10="$("$run" --setup 2>&1)"
rc10=$?
set -e
[[ "$rc10" -eq 2 ]] || fail "D10 want 2 got $rc10: $out10"
[[ ! -f "$tmpdir/evil.txt" ]] || fail "D10 tarbomb wrote outside"

# D11: self-contained card copy (no monorepo cwd)
export DEVLOOP_DATA_HOME="$tmpdir/data-copy"
card_copy="$tmpdir/card-copy"
rm -rf "$card_copy"
cp -R "$root/skills/devloop-run" "$card_copy"
# point pin to fixture
cp "$fixture_pin" "$card_copy/references/engine-pin.json"
unset DEVLOOP_ENGINE_PIN
(
  cd /
  out11="$("$card_copy/scripts/devloop-run" --setup 2>&1)" || fail "D11 setup from /: $out11"
  [[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D11 engine missing"
)

# D12: force-bootstrap without marker refuses without --force-hard
export DEVLOOP_DATA_HOME="$tmpdir/data-hand"
mkdir -p "$DEVLOOP_DATA_HOME/devloop/scripts"
printf 'print(1)\n' >"$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py"
# no marker
export DEVLOOP_ENGINE_PIN="$fixture_pin"
set +e
out12="$("$run" --force-bootstrap --setup 2>&1)"
rc12=$?
set -e
[[ "$rc12" -eq 2 ]] || fail "D12 want 2 got $rc12: $out12"
printf '%s\n' "$out12" | grep -qi 'force-hard\|unmarked' || fail "D12 message: $out12"

# D13: concurrent --setup (lock + post-lock re-check) both exit 0
export DEVLOOP_DATA_HOME="$tmpdir/data-conc"
rm -rf "$DEVLOOP_DATA_HOME"
export DEVLOOP_ENGINE_PIN="$fixture_pin"
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL || true
set +e
"$run" --setup >/tmp/devloop-conc-a.$$.out 2>&1 &
pa=$!
"$run" --setup >/tmp/devloop-conc-b.$$.out 2>&1 &
pb=$!
wait "$pa"
rca=$?
wait "$pb"
rcb=$?
set -e
[[ "$rca" -eq 0 && "$rcb" -eq 0 ]] || fail "D13 concurrent setup rcs $rca $rcb: $(cat /tmp/devloop-conc-a.$$.out /tmp/devloop-conc-b.$$.out 2>/dev/null)"
[[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D13 missing engine after concurrent setup"
[[ -f "$DEVLOOP_DATA_HOME/devloop/.skill-craft-engine.json" ]] || fail "D13 missing marker after concurrent setup"
rm -f /tmp/devloop-conc-a.$$.out /tmp/devloop-conc-b.$$.out

# D14: package deny-check rejects host-absolute path leakage
pkg="$root/scripts/package-devloop-engine.sh"
[[ -x "$pkg" ]] || fail "D14 missing package-devloop-engine.sh"
bad_tree="$tmpdir/engine-leaky"
rm -rf "$bad_tree"
mkdir -p "$bad_tree/scripts" "$bad_tree/references"
printf 'print("ok")\n' >"$bad_tree/scripts/devloop_cli.py"
printf 'path /Users/someone/secret/docs\n' >"$bad_tree/references/leak.md"
set +e
out14="$("$pkg" --from "$bad_tree" --version 0.0.0-test --out "$tmpdir/pkg-out" 2>&1)"
rc14=$?
set -e
[[ "$rc14" -ne 0 ]] || fail "D14 want non-zero package exit: $out14"
printf '%s\n' "$out14" | grep -qi 'deny-check' || fail "D14 message: $out14"
# clean mini tree packages ok
clean_tree="$tmpdir/engine-clean"
rm -rf "$clean_tree"
mkdir -p "$clean_tree/scripts"
printf 'print("ok")\n' >"$clean_tree/scripts/devloop_cli.py"
out14b="$("$pkg" --from "$clean_tree" --version 0.0.0-ok --out "$tmpdir/pkg-out" 2>&1)" || fail "D14 clean package: $out14b"
[[ -f "$tmpdir/pkg-out/devloop-engine-0.0.0-ok.tar.gz" ]] || fail "D14 missing tgz"

# D15: --setup without python3 → exit 2 (not bare 127)
export DEVLOOP_DATA_HOME="$tmpdir/data-nopy"
export DEVLOOP_ENGINE_PIN="$fixture_pin"
unset DEVLOOP_HOME HERMES_HOME || true
# PATH with only coreutils-ish bins; no python3
nopy_bin="$tmpdir/nopy-bin"
mkdir -p "$nopy_bin"
for c in bash sh mkdir cat cp rm mv ls true false grep awk sed env; do
  if command -v "$c" >/dev/null 2>&1; then
    ln -sf "$(command -v "$c")" "$nopy_bin/$c" 2>/dev/null || true
  fi
done
# ensure python3 not present
[[ ! -e "$nopy_bin/python3" ]] || rm -f "$nopy_bin/python3"
set +e
out15="$(PATH="$nopy_bin" "$run" --setup 2>&1)"
rc15=$?
set -e
[[ "$rc15" -eq 2 ]] || fail "D15 want 2 got $rc15: $out15"
printf '%s\n' "$out15" | grep -qi 'python3' || fail "D15 message: $out15"

# D16: honesty / version
grep -q 'Hermes-default\|Hermes-default' "$root/skills/devloop-run/SKILL.md" \
  || grep -qi 'Hermes' "$root/skills/devloop-run/SKILL.md" || fail "D16 honesty Hermes"
grep -E '^version: 0\.3\.' "$root/skills/devloop-run/SKILL.md" || fail "D16 version 0.3.x"

# D17: DEVLOOP_BOOTSTRAP_CMD success
export DEVLOOP_DATA_HOME="$tmpdir/data-cmd"
rm -rf "$DEVLOOP_DATA_HOME"
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_ENGINE_URL DEVLOOP_ENGINE_PIN || true
export DEVLOOP_BOOTSTRAP_CMD="$tmpdir/bootstrap-cmd.sh"
cat >"$DEVLOOP_BOOTSTRAP_CMD" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
dest="$1"
mkdir -p "$dest/scripts"
printf 'print("BOOTSTRAP_CMD_ENGINE")\n' >"$dest/scripts/devloop_cli.py"
SH
chmod +x "$DEVLOOP_BOOTSTRAP_CMD"
out17="$("$run" --setup 2>&1)" || fail "D17 setup: $out17"
[[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D17 engine missing"
out17r="$("$run" --no-bootstrap -- hi 2>&1)" || fail "D17 run: $out17r"
printf '%s\n' "$out17r" | grep -q 'BOOTSTRAP_CMD_ENGINE' || fail "D17 run output: $out17r"

# D18: DEVLOOP_BOOTSTRAP_CMD fail → exit 2
export DEVLOOP_DATA_HOME="$tmpdir/data-cmd-fail"
rm -rf "$DEVLOOP_DATA_HOME"
export DEVLOOP_BOOTSTRAP_CMD="$tmpdir/bootstrap-fail.sh"
printf '#!/usr/bin/env bash\nexit 1\n' >"$DEVLOOP_BOOTSTRAP_CMD"
chmod +x "$DEVLOOP_BOOTSTRAP_CMD"
set +e
out18="$("$run" --setup 2>&1)"
rc18=$?
set -e
[[ "$rc18" -eq 2 ]] || fail "D18 want 2 got $rc18: $out18"
printf '%s\n' "$out18" | grep -qi 'BOOTSTRAP_CMD\|failed\|bootstrap' || fail "D18 message: $out18"
[[ ! -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D18 partial install"

# D19: --force-bootstrap --force-hard replaces unmarked tree
export DEVLOOP_DATA_HOME="$tmpdir/data-force-hard"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME/devloop/scripts"
printf 'print("OLD")\n' >"$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py"
# no marker
unset DEVLOOP_BOOTSTRAP_CMD DEVLOOP_HOME HERMES_HOME || true
export DEVLOOP_ENGINE_PIN="$fixture_pin"
out19="$("$run" --force-bootstrap --force-hard --setup 2>&1)" || fail "D19 setup: $out19"
[[ -f "$DEVLOOP_DATA_HOME/devloop/.skill-craft-engine.json" ]] || fail "D19 marker missing"
out19r="$("$run" --no-bootstrap -- hi 2>&1)" || fail "D19 run: $out19r"
printf '%s\n' "$out19r" | grep -q 'FIXTURE_ENGINE' || fail "D19 fixture run: $out19r"

# D20: resolve engine from HERMES_HOME seed (no host-local, no pin download)
export DEVLOOP_DATA_HOME="$tmpdir/data-seed-empty"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME"
unset DEVLOOP_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL || true
export HERMES_HOME="$tmpdir/hermes-seed"
mkdir -p "$HERMES_HOME/skills/software-development/devloop/scripts"
printf 'print("SEED_ENGINE")\n' >"$HERMES_HOME/skills/software-development/devloop/scripts/devloop_cli.py"
export DEVLOOP_ENGINE_PIN="$tmpdir/empty-pin.json"
printf '%s\n' '{"version":"x","url":"REPLACE_WITH_RELEASE_URL/x.tgz","sha256":""}' >"$DEVLOOP_ENGINE_PIN"
out20p="$("$run" --probe --no-bootstrap 2>&1)" || fail "D20 probe: $out20p"
printf '%s\n' "$out20p" | grep -q 'engine=' || fail "D20 probe engine=: $out20p"
printf '%s\n' "$out20p" | grep -q 'hermes-seed\|SEED\|devloop' || fail "D20 probe selected seed: $out20p"
out20r="$("$run" --no-bootstrap -- hi 2>&1)" || fail "D20 run: $out20r"
printf '%s\n' "$out20r" | grep -q 'SEED_ENGINE' || fail "D20 run output: $out20r"

# D21: bootstrap_engine seed-copy path (--force-bootstrap with REPLACE pin + HERMES seed)
# Resolve would find the seed; force-bootstrap skips resolve and seed-copies into host-local.
export DEVLOOP_DATA_HOME="$tmpdir/data-seed-copy"
rm -rf "$DEVLOOP_DATA_HOME"
unset DEVLOOP_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL || true
export HERMES_HOME="$tmpdir/hermes-seed-copy"
mkdir -p "$HERMES_HOME/skills/software-development/devloop/scripts"
printf 'print("SEED_COPY_ENGINE")\n' >"$HERMES_HOME/skills/software-development/devloop/scripts/devloop_cli.py"
export DEVLOOP_ENGINE_PIN="$tmpdir/replace-pin.json"
printf '%s\n' '{"version":"seed","url":"REPLACE_WITH_RELEASE_URL/x.tgz","sha256":""}' >"$DEVLOOP_ENGINE_PIN"
out21="$("$run" --force-bootstrap --force-hard --setup 2>&1)" || fail "D21 seed-copy setup: $out21"
printf '%s\n' "$out21" | grep -qi 'seed' || fail "D21 setup should seed-copy: $out21"
[[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D21 host-local engine missing after seed-copy"
[[ -f "$DEVLOOP_DATA_HOME/devloop/.skill-craft-engine.json" ]] || fail "D21 marker missing after seed-copy"
# Must run from host-local, not only via resolve to HERMES_HOME
unset HERMES_HOME
out21r="$("$run" --no-bootstrap -- hi 2>&1)" || fail "D21 run host-local: $out21r"
printf '%s\n' "$out21r" | grep -q 'SEED_COPY_ENGINE' || fail "D21 host-local run: $out21r"

printf 'devloop-run.test.sh: PASS D1–D21\n'
