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
python3 -c 'import json;d=json.load(open("'"$root"'/skills/devloop-run/references/engine-pin.json")); assert "version" in d and "url" in d and "sha256" in d; assert "grok" in d.get("transports", [])' \
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
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_DATA_HOME DEVLOOP_ENGINE_PIN DEVLOOP_ENGINE_SHA256 \
  DEVLOOP_HOST DEVLOOP_ALLOW_HERMES_SEED DEVLOOP_ALLOW_LEGACY_ENGINE DEVLOOP_DEPTH DEVLOOP_NESTING DEVLOOP_TRANSPORT GROK_BIN || true
export HOME="$tmpdir/empty-home"
mkdir -p "$HOME"
set +e
out1="$("$run" --help 2>&1)"
rc1=$?
set -e
[[ "$rc1" -eq 0 ]] || fail "D1 --help should exit 0 (got $rc1): $out1"
printf '%s\n' "$out1" | grep -qE 'Truth table|--setup|Resolve order|bootstrap' \
  || fail "D1 help missing expected sections: $out1"
printf 'LAYER simple: D1 help OK\n'

# D1b: no engine + --no-bootstrap → exit 2
set +e
out1b="$("$run" --no-bootstrap "noop" 2>&1)"
rc1b=$?
set -e
[[ "$rc1b" -eq 2 ]] || fail "D1b want exit 2 got $rc1b: $out1b"
printf 'LAYER simple: D1b no-bootstrap refuse OK\n'

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
printf 'LAYER simple: D2 DEVLOOP_HOME exec OK\n'

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
grep -q 'references/bootstrap.md' "$root/skills/devloop-run/SKILL.md" || fail "D4 bootstrap pointer"

# D5: no bare skills/devloop
[[ ! -d "$root/skills/devloop" ]] || fail "D5 bare skills/devloop"

# D6: probe
export DEVLOOP_HOME="$eng"
out6="$("$run" --probe 2>&1)" || fail "D6: $out6"
printf '%s\n' "$out6" | grep -q 'engine=' || fail "D6: $out6"
printf 'LAYER simple: D6 probe OK\n'

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
printf 'LAYER integration: D8 setup+probe+exec fixture OK\n'

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

# D16: honesty / version — strict shim, default DevLoop ownership
grep -qi 'Hermes' "$root/skills/devloop-run/SKILL.md" || fail "D16 honesty Hermes host"
grep -qi 'mode=engine' "$root/skills/devloop-run/SKILL.md" || fail "D16 mode=engine banner"
grep -qi 'Forbidden' "$root/skills/devloop-run/SKILL.md" || fail "D16 forbids host loop"
grep -qi 'devloop-native' "$root/skills/devloop-run/SKILL.md" || fail "D16 mentions demoted native"
grep -E '^version: 0\.4\.7' "$root/skills/devloop-run/SKILL.md" || fail "D16 version 0.4.7"
grep -q 'SKILL_ROOT' "$root/skills/devloop-run/SKILL.md" || fail "D16 SKILL_ROOT"
grep -qi 'BEFORE\|STATE\|stderr' "$root/skills/devloop-run/SKILL.md" || fail "D16 inspection/stderr"
[[ -f "$root/skills/devloop-run/references/product-default.md" ]] || fail "D16 product-default.md"

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
printf 'LAYER e2e: D21 force-bootstrap seed-copy + host-local exec OK\n'

# D22: dual-install affinity — host=grok must NOT select Hermes leaf when host-local empty
unset DEVLOOP_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_ALLOW_HERMES_SEED || true
export DEVLOOP_DATA_HOME="$tmpdir/data-dual-empty"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME"
export HERMES_HOME="$tmpdir/hermes-dual"
mkdir -p "$HERMES_HOME/skills/software-development/devloop/scripts"
printf 'print("HERMES_LEAF")\n' >"$HERMES_HOME/skills/software-development/devloop/scripts/devloop_cli.py"
export DEVLOOP_ENGINE_PIN="$tmpdir/empty-pin-dual.json"
printf '%s\n' '{"version":"x","url":"REPLACE_WITH_RELEASE_URL/x.tgz","sha256":""}' >"$DEVLOOP_ENGINE_PIN"
set +e
out22="$("$run" --host grok --probe --no-bootstrap 2>&1)"
rc22=$?
set -e
[[ "$rc22" -eq 2 ]] || fail "D22 want exit 2 (no host-local, hermes disallowed) got $rc22: $out22"
printf '%s\n' "$out22" | grep -qi 'skipping Hermes\|hermes_seed_allowed=0\|engine not resolved\|not resolved' \
  || fail "D22 should skip Hermes seed: $out22"
# Same machine with auto host still may select seed (legacy)
out22b="$("$run" --host auto --probe --no-bootstrap 2>&1)" || fail "D22b auto probe: $out22b"
printf '%s\n' "$out22b" | grep -q 'engine=' || fail "D22b auto should resolve: $out22b"
printf 'LAYER integration: D22 dual-install grok affinity OK\n'

# D23: nesting refuse
export DEVLOOP_HOME="$eng"
unset HERMES_HOME || true
export DEVLOOP_DEPTH=1
set +e
out23="$("$run" --host auto -- hi 2>&1)"
rc23=$?
set -e
[[ "$rc23" -eq 2 ]] || fail "D23 want 2 got $rc23: $out23"
printf '%s\n' "$out23" | grep -qi 'nested\|NESTING\|DEPTH' || fail "D23 message: $out23"
printf '%s\n' "$out23" | grep -qi 'devloop-native' || fail "D23 must mention not native fallback: $out23"
unset DEVLOOP_DEPTH DEVLOOP_NESTING || true
printf 'LAYER simple: D23 nesting refuse OK\n'

# D24: full engine without capabilities + host=grok → exit 2 (honesty)
full_eng="$tmpdir/full-engine-no-cap"
rm -rf "$full_eng"
mkdir -p "$full_eng/scripts" "$full_eng/devloop_core"
printf 'print("FULL")\n' >"$full_eng/scripts/devloop_cli.py"
printf '# stub\n' >"$full_eng/dispatch.py"
printf '# stub\n' >"$full_eng/devloop_bridge.py"
export DEVLOOP_HOME="$full_eng"
# Provide fake grok so binary preflight passes
fake_grok="$tmpdir/fake-grok"
printf '#!/usr/bin/env bash\necho fake-grok\n' >"$fake_grok"
chmod +x "$fake_grok"
export GROK_BIN="$fake_grok"
set +e
out24="$("$run" --host grok -- hi 2>&1)"
rc24=$?
set -e
[[ "$rc24" -eq 2 ]] || fail "D24 want 2 got $rc24: $out24"
printf '%s\n' "$out24" | grep -qi 'capability\|transports\|Grok parity\|ALLOW_LEGACY' \
  || fail "D24 capability message: $out24"
# Legacy allow still runs stub
out24b="$(DEVLOOP_ALLOW_LEGACY_ENGINE=1 "$run" --host grok -- hi 2>&1)" || fail "D24b legacy: $out24b"
printf '%s\n' "$out24b" | grep -q 'FULL' || fail "D24b: $out24b"
printf 'LAYER integration: D24 grok capability preflight OK\n'

# D25: bootstrap.md honesty + host affinity docs
grep -qi 'DEVLOOP_HOST\|host affinity\|ALLOW_HERMES_SEED' "$root/skills/devloop-run/references/bootstrap.md" \
  || fail "D25 bootstrap affinity docs"
grep -qi 'fail closed\|Do not use devloop-native' "$root/skills/devloop-run/references/bootstrap.md" \
  || fail "D25 bootstrap fail-closed docs"
printf 'LAYER simple: D25 bootstrap honesty OK\n'

# D26: invoke via ~/.grok/skills symlink (logical path) with no --host / DEVLOOP_HOST.
# Physical pwd -P must not hide Grok affinity or select a Hermes leaf.
unset DEVLOOP_HOME DEVLOOP_HOST DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_ALLOW_HERMES_SEED \
  DEVLOOP_ALLOW_LEGACY_ENGINE DEVLOOP_TRANSPORT GROK_BIN || true
d26_home="$tmpdir/d26-home"
rm -rf "$d26_home"
mkdir -p "$d26_home/.grok/skills"
ln -s "$root/skills/devloop-run" "$d26_home/.grok/skills/devloop-run"
export HOME="$d26_home"
export DEVLOOP_DATA_HOME="$tmpdir/data-d26-empty"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME"
export HERMES_HOME="$tmpdir/hermes-d26"
mkdir -p "$HERMES_HOME/skills/software-development/devloop/scripts"
printf 'print("HERMES_HIJACK")\n' >"$HERMES_HOME/skills/software-development/devloop/scripts/devloop_cli.py"
export DEVLOOP_ENGINE_PIN="$tmpdir/empty-pin-d26.json"
printf '%s\n' '{"version":"x","url":"REPLACE_WITH_RELEASE_URL/x.tgz","sha256":""}' >"$DEVLOOP_ENGINE_PIN"
d26_run="$d26_home/.grok/skills/devloop-run/scripts/devloop-run"
[[ -x "$d26_run" ]] || fail "D26 symlink invoke path missing: $d26_run"
set +e
out26="$("$d26_run" --probe --no-bootstrap 2>&1)"
rc26=$?
set -e
[[ "$rc26" -eq 2 ]] || fail "D26 want exit 2 (grok symlink, no host-local) got $rc26: $out26"
printf '%s\n' "$out26" | grep -q 'DEVLOOP_HOST=grok' \
  || fail "D26 symlink probe must detect host=grok: $out26"
printf '%s\n' "$out26" | grep -qi 'skipping Hermes\|hermes_seed_allowed=0' \
  || fail "D26 must skip Hermes seed: $out26"
printf '%s\n' "$out26" | grep -qi 'HERMES_HIJACK\|engine=.*/hermes-d26' \
  && fail "D26 must not select Hermes leaf: $out26"
printf 'LAYER integration: D26 grok skill-dir symlink host detect OK\n'

# D27: pin transports omit grok → host=grok bootstrap refuses (before extract)
unset DEVLOOP_HOME DEVLOOP_HOST DEVLOOP_ALLOW_HERMES_SEED DEVLOOP_ALLOW_LEGACY_ENGINE || true
export DEVLOOP_DATA_HOME="$tmpdir/data-d27"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME"
export DEVLOOP_ENGINE_PIN="$tmpdir/pin-no-grok.json"
python3 - "$DEVLOOP_ENGINE_PIN" "$fixture_tgz" <<'PY'
import hashlib, json, pathlib, sys
pin, tgz = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sha = hashlib.sha256(tgz.read_bytes()).hexdigest()
pin.write_text(json.dumps({
    "version": "fixture",
    "url": f"file://{tgz.resolve()}",
    "sha256": sha,
    "transports": ["hermes"],
}, indent=2) + "\n")
PY
set +e
out27="$("$run" --host grok --force-bootstrap --force-hard --setup 2>&1)"
rc27=$?
set -e
[[ "$rc27" -eq 2 ]] || fail "D27 want exit 2 got $rc27: $out27"
printf '%s\n' "$out27" | grep -qi 'transports without "grok"\|declares transports without' \
  || fail "D27 pin transports message: $out27"
[[ ! -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D27 must not install"
printf 'LAYER integration: D27 pin without grok transport refused OK\n'

# D28: identity banner + BEFORE/AFTER/STATE on probe success and fail-closed
unset DEVLOOP_HOME DEVLOOP_HOST DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_ALLOW_HERMES_SEED \
  DEVLOOP_ALLOW_LEGACY_ENGINE DEVLOOP_TRANSPORT GROK_BIN || true
export DEVLOOP_HOME="$eng"
out28="$("$run" --probe --no-bootstrap 2>&1)" || fail "D28 probe: $out28"
printf '%s\n' "$out28" | grep -q 'DevLoop — mode=engine' || fail "D28 identity: $out28"
printf '%s\n' "$out28" | grep -q '\[devloop-run\] BEFORE detect_host' || fail "D28 BEFORE detect: $out28"
printf '%s\n' "$out28" | grep -q '\[devloop-run\] AFTER  detect_host' || fail "D28 AFTER detect: $out28"
printf '%s\n' "$out28" | grep -q '\[devloop-run\] BEFORE resolve_engine' || fail "D28 BEFORE resolve: $out28"
printf '%s\n' "$out28" | grep -q '\[devloop-run\] AFTER  resolve_engine' || fail "D28 AFTER resolve: $out28"
printf '%s\n' "$out28" | grep -q '\[devloop-run\] STATE  life=resolve' || fail "D28 STATE resolve: $out28"
unset DEVLOOP_HOME || true
export DEVLOOP_DATA_HOME="$tmpdir/data-d28-empty"
rm -rf "$DEVLOOP_DATA_HOME"
mkdir -p "$DEVLOOP_DATA_HOME"
export DEVLOOP_ENGINE_PIN="$tmpdir/empty-pin-d28.json"
printf '%s\n' '{"version":"x","url":"REPLACE_WITH_RELEASE_URL/x.tgz","sha256":""}' >"$DEVLOOP_ENGINE_PIN"
set +e
out28b="$("$run" --host grok --probe --no-bootstrap 2>&1)"
rc28b=$?
set -e
[[ "$rc28b" -eq 2 ]] || fail "D28b want exit 2 got $rc28b: $out28b"
printf '%s\n' "$out28b" | grep -q 'DevLoop — mode=engine' || fail "D28b identity: $out28b"
printf '%s\n' "$out28b" | grep -q '\[devloop-run\] STATE  life=fail-closed' \
  || fail "D28b STATE fail-closed: $out28b"
printf 'LAYER integration: D28 identity+lifecycle traces OK\n'

# D29: new-repo designation — --repo flag always wins, even with designation text present
unset DEVLOOP_HOME DEVLOOP_HOST DEVLOOP_DATA_HOME DEVLOOP_ENGINE_PIN DEVLOOP_ENGINE_URL \
  DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ALLOW_HERMES_SEED DEVLOOP_ALLOW_LEGACY_ENGINE \
  DEVLOOP_TRANSPORT GROK_BIN HERMES_HOME || true
export DEVLOOP_HOME="$eng"
out29="$("$run" -- --repo /tmp/x "start a new repo for this" 2>&1)" || fail "D29: $out29"
printf '%s\n' "$out29" | grep -q 'STATE target=explicit reason=repo_flag' || fail "D29 repo_flag: $out29"
printf 'LAYER simple: D29 --repo wins over designation text OK\n'

# D30: no --repo + designation phrase -> scratch + new_repo_designated (positive, case-insensitive)
for phrase in "new repo" "NEW REPO" "new repository" "separate repo" "fresh repo" "create a repo" "newly created repo"; do
  out30="$("$run" -- "please set up a ${phrase} for this feature" 2>&1)" || fail "D30 ($phrase): $out30"
  printf '%s\n' "$out30" | grep -q 'STATE target=scratch reason=new_repo_designated' \
    || fail "D30 ($phrase) missing designation STATE: $out30"
done
printf 'LAYER simple: D30 new-repo phrase detection (positive) OK\n'

# D31: no --repo + no designation -> unchanged default (still scratch, reason=default)
out31="$("$run" -- "fix the bug in the parser" 2>&1)" || fail "D31: $out31"
printf '%s\n' "$out31" | grep -q 'STATE target=scratch reason=default' || fail "D31 default: $out31"
printf 'LAYER simple: D31 default scratch reason OK\n'

# D32: negative phrases must NOT trigger designation (conservative detector, no fuzzy match)
for phrase in "existing repo" "repository survey" "the repo is old" "reporting new results"; do
  out32="$("$run" -- "please work in the ${phrase}" 2>&1)" || fail "D32 ($phrase): $out32"
  printf '%s\n' "$out32" | grep -q 'STATE target=scratch reason=default' \
    || fail "D32 ($phrase) should stay default: $out32"
  printf '%s\n' "$out32" | grep -q 'new_repo_designated' \
    && fail "D32 ($phrase) falsely designated: $out32"
done
printf 'LAYER simple: D32 negative phrase guard OK\n'

# D33: card documents new-repo + /devloop prompt form (no fuzzy cwd/last-path guessing)
grep -qi 'new repo' "$root/skills/devloop-run/SKILL.md" || fail "D33 SKILL.md new repo"
grep -q 'new_repo_designated' "$root/skills/devloop-run/SKILL.md" || fail "D33 SKILL.md STATE line"
grep -qi 'infer cwd' "$root/skills/devloop-run/SKILL.md" || fail "D33 SKILL.md no-infer-cwd"
grep -q "grok -p '/devloop" "$root/skills/devloop-run/SKILL.md" || fail "D33 SKILL.md grok -p /devloop"
printf 'LAYER simple: D33 SKILL.md designation docs OK\n'

# D34: verify_cmd exactly [ with no --lang -> shim must NOT auto-prepend --lang
# command. Host interpolation, not shim prose-scraping, decides --lang.
out34="$("$run" -- 'new repo. verify_cmd exactly ["test", "-f", "result.txt"]' 2>&1)" || fail "D34: $out34"
printf '%s\n' "$out34" | grep -q 'STATE lang=command reason=verify_cmd_exactly' \
  && fail "D34 must not auto-prepend --lang from prose: $out34"
printf '%s\n' "$out34" | grep -q 'STUB_CLI --lang command' \
  && fail "D34 must not prepend --lang command: $out34"
printf '%s\n' "$out34" | grep -q 'STATE lang=none reason=none' \
  || fail "D34 missing STATE lang=none when no --lang passed: $out34"
printf 'LAYER simple: D34 no auto --lang from verify_cmd exactly (host must pass --lang) OK\n'

# D35: explicit --lang always wins and is forwarded; STATE reflects it verbatim.
out35="$("$run" -- --lang python 'verify_cmd exactly ["true"]' 2>&1)" || fail "D35: $out35"
printf '%s\n' "$out35" | grep -q 'STATE lang=python reason=explicit' \
  || fail "D35 missing explicit lang STATE: $out35"
printf '%s\n' "$out35" | grep -q 'STUB_CLI --lang python' \
  || fail "D35 lost explicit --lang: $out35"
printf 'LAYER simple: D35 explicit --lang wins + STATE lang=<value> reason=explicit OK\n'

# D36: no verify_cmd / no --lang -> do not invent --lang; STATE lang=none reason=none
out36="$("$run" -- "fix the bug in the parser" 2>&1)" || fail "D36: $out36"
printf '%s\n' "$out36" | grep -q 'STATE lang=none reason=none' \
  || fail "D36 missing STATE lang=none: $out36"
printf '%s\n' "$out36" | grep -q 'STUB_CLI --lang' \
  && fail "D36 forwarded --lang without a signal: $out36"
printf 'LAYER simple: D36 no verify_cmd leaves lang alone, STATE lang=none OK\n'

# D37: SKILL.md hermetic string checks — /devloop + interpolate procedure,
# COMPLETE = AFTER exec exit=0, no /goal or /loop invoke.
grep -qi 'interpolate' "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md mentions interpolate"
grep -qi 'print the interpolation' "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md prints interpolation"
grep -qi 'fail-closed' "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md fail-closed"
grep -qi 'checkable done' "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md checkable-done language"
grep -q 'AFTER exec exit=0' "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md COMPLETE = AFTER exec exit=0"
grep -q "grok -p '/devloop" "$root/skills/devloop-run/SKILL.md" || fail "D37 SKILL.md grok -p /devloop"
printf '%s\n' "$(grep -c "grok -p '/goal" "$root/skills/devloop-run/SKILL.md" || true)" | grep -q '^0$' \
  || fail "D37 SKILL.md must not invoke /goal"
printf '%s\n' "$(grep -c "grok -p '/loop" "$root/skills/devloop-run/SKILL.md" || true)" | grep -q '^0$' \
  || fail "D37 SKILL.md must not invoke /loop"
printf 'LAYER simple: D37 SKILL.md interpolation procedure docs OK\n'

# D39: flags-free default — parse skill argument, interpolate argv; user not
# required to pass the four engine flags. Distinct greps so one revert fails.
card="$root/skills/devloop-run/SKILL.md"
grep -qi 'flags-free' "$card" || fail "D39 SKILL.md flags-free default"
grep -qi 'parse that text' "$card" || grep -qi 'parses skill arguments' "$card" \
  || fail "D39 SKILL.md parse skill argument"
grep -qi 'interpolate' "$card" || fail "D39 SKILL.md interpolate"
grep -q -- '--repo' "$card" && grep -q -- '--lang' "$card" \
  && grep -q 'verify_cmd exactly' "$card" && grep -q -- '--setup-spec' "$card" \
  || fail "D39 SKILL.md names the four optional flags"
grep -qi 'not required to type any of these' "$card" \
  || grep -qi 'do not require the user to pass' "$card" \
  || fail "D39 SKILL.md user not required to pass flags"
printf 'LAYER simple: D39 SKILL.md flags-free parse/interpolate OK\n'

# D40: /goal-shaped phase complete-whens (directives, not harness). SETUP gated.
grep -q '| DEFINE |' "$card" || fail "D40 SKILL.md DEFINE complete-when"
grep -q '| PROVE |' "$card" || fail "D40 SKILL.md PROVE complete-when"
grep -q '| BUILD |' "$card" || fail "D40 SKILL.md BUILD complete-when"
grep -q '| DELIVER |' "$card" || fail "D40 SKILL.md DELIVER complete-when"
grep -qi 'complete-when' "$card" || grep -qi 'Complete when' "$card" \
  || fail "D40 SKILL.md complete-when dialect"
grep -qi 'only if user named new GAS' "$card" \
  || grep -qi 'SETUP (only if user named new GAS' "$card" \
  || fail "D40 SKILL.md SETUP gated on new GAS/mcp/hosted"
printf '%s\n' "$(grep -c "grok -p '/goal" "$card" || true)" | grep -q '^0$' \
  || fail "D40 SKILL.md must not invoke grok -p /goal"
printf '%s\n' "$(grep -c "grok -p '/loop" "$card" || true)" | grep -q '^0$' \
  || fail "D40 SKILL.md must not invoke grok -p /loop"
printf 'LAYER simple: D40 SKILL.md phase complete-whens + no harness invoke OK\n'

# D38: STATE lang=... is always emitted, whatever reached the CLI.
out38a="$("$run" -- "no signals here" 2>&1)" || fail "D38a: $out38a"
printf '%s\n' "$out38a" | grep -q 'STATE lang=none reason=none' \
  || fail "D38a no-lang invoke must print STATE lang=none reason=none: $out38a"
out38b="$("$run" -- --lang command "verify_cmd exactly [\"true\"]" 2>&1)" || fail "D38b: $out38b"
printf '%s\n' "$out38b" | grep -q 'STATE lang=command reason=explicit' \
  || fail "D38b explicit --lang command must print STATE lang=command reason=explicit: $out38b"
printf 'LAYER simple: D38 STATE lang always emitted OK\n'

# D41: Grok /devloop alias stays aligned (file Grok loads). Optional path
# override: DEVLOOP_ALIAS_MD. Distinct from the card so alias drift fails here.
alias_md="${DEVLOOP_ALIAS_MD:-}"
if [[ -z "$alias_md" ]]; then
  if [[ -f "$root/../grok-build-additions/commands/devloop.md" ]]; then
    alias_md="$root/../grok-build-additions/commands/devloop.md"
  elif [[ -f "${HOME}/.grok/commands/devloop.md" ]]; then
    alias_md="${HOME}/.grok/commands/devloop.md"
  fi
fi
if [[ -z "$alias_md" || ! -f "$alias_md" ]]; then
  fail "D41 /devloop alias file not found (set DEVLOOP_ALIAS_MD)"
fi
grep -qi 'do not mandate engine flags' "$alias_md" \
  || grep -qi 'do not require flags' "$alias_md" \
  || fail "D41 alias flags-free: $alias_md"
grep -qi 'skill argument' "$alias_md" || fail "D41 alias skill-argument parse: $alias_md"
grep -qi 'interpolate' "$alias_md" || fail "D41 alias interpolate: $alias_md"
grep -qi 'do not invoke the host goal harness' "$alias_md" \
  || fail "D41 alias no-host-goal-harness-as-loop: $alias_md"
printf '%s\n' "$(grep -c "grok -p '/goal" "$alias_md" || true)" | grep -q '^0$' \
  || fail "D41 alias must not invoke grok -p /goal"
printf 'LAYER simple: D41 /devloop alias alignment OK (%s)\n' "$alias_md"

printf 'devloop-run.test.sh: PASS D1–D41\n'
