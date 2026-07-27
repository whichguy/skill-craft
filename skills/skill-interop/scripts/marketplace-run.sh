#!/usr/bin/env bash
# marketplace-run.sh — generic marketplace facade over Claude / Grok / Codex plugins.
#
# Exit codes:
#   0  ok (all selected available hosts succeeded; hosts verb always 0 when emitted)
#   1  one or more selected available hosts failed (partial multi-host fail)
#   2  usage / bad args
#   3  no selected host is available (bin missing) for an operation that needs one
#   4  host-specific precondition failed before CLI
#      (Codex bare name without @; Grok Claude-style name@marketplace)
#
# Multi-host policy: exit 1 if ANY selected available host fails.
# Missing CLIs are reported as unavailable and skipped (not a failure by themselves).
#
# Env overrides (testable):
#   CLAUDE_BIN  CODEX_BIN  GROK_BIN   (default: command -v claude|codex|grok)
#   MARKETPLACE_INSTALL_SH            (default: <repo>/install.sh for install-local)
set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: marketplace-run.sh <verb...> [options]

Verbs:
  hosts
  marketplaces list
  marketplaces add <src>
  marketplaces update [name]
  plugins list [--q QUERY]
  plugins install <id>
  plugins uninstall <id>
  plugins update [id]
  install-local [skill-args...]   # exec repo install.sh (skill-dir side-load)

Global:
  --host claude|grok|codex|all   (default: all)
  --json
  --dry-run
  -h|--help

Exit codes: 0 ok · 1 any available host failed · 2 usage · 3 no host available · 4 precondition
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Walk up from script_dir until a dir contains install.sh OR .git (prefer install.sh).
# Cap depth so a relocated/broken tree fails clearly instead of scanning the whole FS.
find_repo_dir() {
  local start="$1"
  local max_depth="${2:-8}"
  local cur="$start"
  local depth=0
  local found_git=""
  while [[ "$depth" -le "$max_depth" ]]; do
    if [[ -f "$cur/install.sh" ]]; then
      printf '%s' "$cur"
      return 0
    fi
    # .git may be a directory (normal clone) or a file (worktree / gitdir pointer).
    if [[ -z "$found_git" && -e "$cur/.git" ]]; then
      found_git="$cur"
    fi
    local parent
    parent="$(cd "$cur/.." && pwd -P)"
    if [[ "$parent" == "$cur" ]]; then
      break
    fi
    cur="$parent"
    depth=$((depth + 1))
  done
  if [[ -n "$found_git" ]]; then
    printf '%s' "$found_git"
    return 0
  fi
  return 1
}

repo_dir=""
if ! repo_dir="$(find_repo_dir "$script_dir" 8)"; then
  # install-local still allows MARKETPLACE_INSTALL_SH override; other verbs don't need repo_dir.
  repo_dir=""
fi

# ---------------------------------------------------------------------------
# Globals / defaults
# ---------------------------------------------------------------------------
HOST_FILTER="all"
JSON_OUT=0
DRY_RUN=0
PLUGIN_Q=""
ANY_HOST_FAILED=0
HAD_AVAILABLE_HOST=0
# Exit 4 when a host precondition fails (Codex bare name, Grok Claude-style id).
PRECONDITION_FAILED=0

declare -a SELECTED_HOSTS=()

# Claude-style marketplace plugin id: name@marketplace with no path/scheme.
# Grok treats @ as a git ref, so the facade rejects this form for --host grok.
is_claude_style_marketplace_id() {
  local id="$1"
  # Must contain exactly one @, no scheme (://), no path slash, no git@ host form.
  [[ "$id" != *"://"* ]] || return 1
  [[ "$id" != *"/"* ]] || return 1
  [[ "$id" == *@* ]] || return 1
  [[ "$id" != *@*@* ]] || return 1
  # name and marketplace: non-empty safe leaves
  [[ "$id" =~ ^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+$ ]]
}

resolve_bin() {
  local host="$1"
  local env_var override
  case "$host" in
    claude) env_var=CLAUDE_BIN; override="${CLAUDE_BIN:-}" ;;
    codex)  env_var=CODEX_BIN;  override="${CODEX_BIN:-}" ;;
    grok)   env_var=GROK_BIN;   override="${GROK_BIN:-}" ;;
    *) printf 'internal: unknown host %s\n' "$host" >&2; return 1 ;;
  esac
  if [[ -n "$override" ]]; then
    printf '%s' "$override"
    return 0
  fi
  command -v "$host" 2>/dev/null || true
}

bin_available() {
  local bin="$1"
  [[ -n "$bin" && -x "$bin" ]] || [[ -n "$bin" && -f "$bin" ]]
}

# True if PATH/env points at something we can attempt to exec
host_is_available() {
  local host="$1"
  local bin
  bin="$(resolve_bin "$host")"
  [[ -n "$bin" ]] && { [[ -x "$bin" ]] || command -v "$bin" >/dev/null 2>&1 || [[ -f "$bin" ]]; }
}

emit_json() {
  python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2, ensure_ascii=False))'
}

# ---------------------------------------------------------------------------
# Arg parse — global flags may appear anywhere; verbs are positional
# ---------------------------------------------------------------------------
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --host)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --host\n' >&2
        usage
        exit 2
      fi
      HOST_FILTER="$2"
      shift 2
      ;;
    --json)
      JSON_OUT=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --q)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --q\n' >&2
        usage
        exit 2
      fi
      PLUGIN_Q="$2"
      shift 2
      ;;
    --)
      shift
      ARGS+=("$@")
      break
      ;;
    -*)
      printf 'Unknown flag: %s\n' "$1" >&2
      usage
      exit 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

set -- "${ARGS[@]+"${ARGS[@]}"}"

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

case "$HOST_FILTER" in
  all)
    SELECTED_HOSTS=(claude grok codex)
    ;;
  claude|grok|codex)
    SELECTED_HOSTS=("$HOST_FILTER")
    ;;
  *)
    printf 'Invalid --host %q (want claude|grok|codex|all)\n' "$HOST_FILTER" >&2
    exit 2
    ;;
esac

verb1="${1:-}"
verb2="${2:-}"

# ---------------------------------------------------------------------------
# Host capability matrix
# ---------------------------------------------------------------------------
# All three hosts support the same high-level surface for B1/B2.
# install_git: host accepts git/path as plugin id (grok yes; claude marketplace-mediated;
# codex name@marketplace only via this facade).
cmd_hosts() {
  local host bin status
  local -a rows=()
  for host in "${SELECTED_HOSTS[@]}"; do
    bin="$(resolve_bin "$host")"
    if host_is_available "$host"; then
      status="available"
    else
      status="unavailable"
      bin=""
    fi
    rows+=("$(python3 -c '
import json,sys
host,status,binpath=sys.argv[1],sys.argv[2],sys.argv[3]
caps={
  "list_marketplaces": True,
  "add_marketplace": True,
  "list_plugins": True,
  "install_plugin": True,
  "install_git": host == "grok",
  "update": True,
}
print(json.dumps({
  "host": host,
  "status": status,
  "bin": binpath or None,
  "capabilities": caps,
}))
' "$host" "$status" "$bin")")
  done

  if [[ "$JSON_OUT" -eq 1 ]]; then
    python3 -c '
import json,sys
rows=[json.loads(l) for l in sys.stdin if l.strip()]
print(json.dumps({"hosts": rows}, indent=2, ensure_ascii=False))
' <<<"$(printf '%s\n' "${rows[@]}")"
  else
    printf '%-8s %-12s %-40s %s\n' "HOST" "STATUS" "BIN" "CAPABILITIES"
    for row in "${rows[@]}"; do
      python3 -c '
import json,sys
r=json.loads(sys.argv[1])
caps=",".join(k for k,v in r["capabilities"].items() if v)
print("%-8s %-12s %-40s %s" % (r["host"], r["status"], r.get("bin") or "-", caps))
' "$row"
    done
  fi
}

# ---------------------------------------------------------------------------
# Run helper: capture status without set -e death; optional dry-run print
# ---------------------------------------------------------------------------
# Sets: LAST_EC LAST_STDOUT LAST_STDERR LAST_ARGV_JSON
run_host_cmd() {
  local dry="$1"
  shift
  local -a argv=("$@")
  LAST_ARGV_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "${argv[@]}")"
  if [[ "$dry" -eq 1 ]]; then
    printf 'would-run: %s\n' "$(python3 -c 'import json,sys; print(" ".join(json.loads(sys.argv[1])))' "$LAST_ARGV_JSON")"
    LAST_EC=0
    LAST_STDOUT=""
    LAST_STDERR=""
    return 0
  fi
  local out_file err_file
  out_file="$(mktemp)"
  err_file="$(mktemp)"
  set +e
  "${argv[@]}" >"$out_file" 2>"$err_file"
  LAST_EC=$?
  set -e
  LAST_STDOUT="$(cat "$out_file")"
  LAST_STDERR="$(cat "$err_file")"
  rm -f "$out_file" "$err_file"
  return 0
}

note_host_result() {
  local host="$1"
  local op="$2"
  local ec="$3"
  HAD_AVAILABLE_HOST=1
  if [[ "$ec" -ne 0 ]]; then
    ANY_HOST_FAILED=1
    printf 'marketplace-run: host=%s op=%s exit=%s\n' "$host" "$op" "$ec" >&2
    if [[ -n "${LAST_STDERR:-}" ]]; then
      printf '%s\n' "$LAST_STDERR" >&2
    fi
  fi
}

skip_unavailable() {
  local host="$1"
  printf 'marketplace-run: host=%s status=unavailable (skipped)\n' "$host" >&2
}

# ---------------------------------------------------------------------------
# Parsers (best-effort; on failure attach raw)
# ---------------------------------------------------------------------------
parse_marketplaces() {
  local host="$1"
  local text="$2"
  python3 - "$host" "$text" <<'PY'
import json, re, sys
host, text = sys.argv[1], sys.argv[2]
lines = text.splitlines()
out = []

def add(name, source=None, status=None, raw=None):
    item = {"host": host, "name": name}
    if source is not None:
        item["source"] = source
    if status is not None:
        item["status"] = status
    if raw is not None:
        item["raw"] = raw
    out.append(item)

try:
    stripped = text.strip()
    # Prefer JSON when the whole payload is structured (Claude --json, etc.)
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(stripped)
        items = []
        if isinstance(data, dict):
            items = (
                data.get("marketplaces")
                or data.get("installed")
                or data.get("items")
                or data.get("configured")
                or []
            )
            if isinstance(items, dict):
                items = list(items.values()) if items else []
            # single object with name
            if not items and data.get("name"):
                items = [data]
        elif isinstance(data, list):
            items = data
        for m in items:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or m.get("id") or m.get("marketplace") or ""
            if not name:
                continue
            add(
                name,
                source=m.get("source") or m.get("url") or m.get("root") or m.get("path"),
                status=m.get("status"),
            )
        if out:
            print(json.dumps(out, ensure_ascii=False))
            raise SystemExit(0)

    if host == "claude":
        # "  ❯ name" then optional "    Source: ..."
        name = None
        for line in lines:
            m = re.match(r"^\s*[❯>*-]?\s*([A-Za-z0-9._-]+)\s*$", line)
            if m and "Configured marketplaces" not in line and "Source:" not in line:
                # skip header-ish
                cand = m.group(1)
                if cand.lower() in ("configured", "marketplaces", "source"):
                    continue
                if name is not None and not any(x["name"] == name for x in out):
                    add(name)
                name = cand
                continue
            sm = re.search(r"Source:\s*(.+)\s*$", line)
            if sm and name:
                add(name, source=sm.group(1).strip())
                name = None
                continue
            # plain "name" lines without bullet after header
            m2 = re.match(r"^\s+([A-Za-z0-9._-]+)\s*$", line)
            if m2 and "Source:" not in line:
                cand = m2.group(1)
                if name is not None and not any(x["name"] == name for x in out):
                    add(name)
                name = cand
        if name is not None and not any(x["name"] == name for x in out):
            add(name)
        # fallback: if nothing parsed, try bullet names only
        if not out:
            for line in lines:
                m = re.search(r"[❯>]\s*([A-Za-z0-9._-]+)", line)
                if m:
                    add(m.group(1), raw=line.strip())

    elif host == "codex":
        # "MARKETPLACE ROOT" header then "name path"
        for line in lines:
            if re.match(r"^\s*MARKETPLACE\s+ROOT\s*$", line, re.I):
                continue
            if not line.strip():
                continue
            parts = re.split(r"\s+", line.strip(), maxsplit=1)
            if len(parts) == 2 and parts[0].lower() != "marketplace":
                add(parts[0], source=parts[1])
            elif len(parts) == 1:
                add(parts[0])

    elif host == "grok":
        # "  name: url" or "name: url"
        for line in lines:
            m = re.match(r"^\s*([^:]+):\s*(\S+)\s*$", line)
            if m:
                add(m.group(1).strip(), source=m.group(2).strip())
            elif line.strip():
                # bare name
                m2 = re.match(r"^\s*([A-Za-z0-9._-]+)\s*$", line)
                if m2:
                    add(m2.group(1))

    if not out and text.strip():
        for line in lines:
            if line.strip():
                out.append({"host": host, "name": None, "raw": line.rstrip()})
except SystemExit:
    raise
except Exception:
    out = [{"host": host, "name": None, "raw": line} for line in lines if line.strip()] or [
        {"host": host, "name": None, "raw": text}
    ]

print(json.dumps(out, ensure_ascii=False))
PY
}

parse_plugins() {
  local host="$1"
  local text="$2"
  local q="${3:-}"
  python3 - "$host" "$text" "$q" <<'PY'
import json, re, sys
host, text, q = sys.argv[1], sys.argv[2], sys.argv[3]
lines = text.splitlines()
out = []

def add(**kw):
    item = {"host": host, "kind": "plugin"}
    item.update(kw)
    out.append(item)

try:
    # Prefer JSON if whole payload is JSON (Claude/Codex/Grok --json)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(stripped)
        plugins = []
        if isinstance(data, dict):
            plugins = data.get("plugins") or data.get("installed") or data.get("items") or []
            if isinstance(plugins, dict):
                plugins = list(plugins.values())
        elif isinstance(data, list):
            plugins = data
        for p in plugins:
            if not isinstance(p, dict):
                continue
            pid = p.get("pluginId") or p.get("id") or ""
            name = p.get("name") or (str(pid).split("@")[0] if pid else "")
            mp = p.get("marketplaceName") or p.get("marketplace") or ""
            if not mp and "@" in str(pid):
                mp = str(pid).split("@", 1)[1]
            if "enabled" in p:
                status = "enabled" if p.get("enabled") else "disabled"
            elif p.get("installed"):
                status = "installed"
            else:
                status = p.get("status") or "unknown"
            add(
                id=pid or (f"{name}@{mp}" if name and mp else name),
                name=name,
                marketplace=mp or None,
                status=status,
                version=p.get("version"),
            )
    elif host == "claude":
        # "  ❯ name@marketplace" + Version/Scope/Status lines
        cur = None
        for line in lines:
            m = re.search(r"[❯>]\s*([A-Za-z0-9._-]+)@([A-Za-z0-9._-]+)", line)
            if m:
                if cur:
                    out.append(cur)
                cur = {
                    "host": host,
                    "kind": "plugin",
                    "id": f"{m.group(1)}@{m.group(2)}",
                    "name": m.group(1),
                    "marketplace": m.group(2),
                    "status": "unknown",
                    "version": None,
                }
                continue
            if cur is None:
                continue
            vm = re.search(r"Version:\s*(\S+)", line)
            if vm:
                cur["version"] = vm.group(1)
            sm = re.search(r"Status:\s*(.+)$", line)
            if sm:
                st = sm.group(1).strip()
                st = re.sub(r"^[✔✓✗×]\s*", "", st).strip()
                cur["status"] = st
        if cur:
            out.append(cur)
    elif host == "grok":
        # human list or "No plugins installed"
        if re.search(r"No plugins installed", text, re.I):
            pass
        else:
            for line in lines:
                m = re.match(r"^\s*[-*]?\s*([A-Za-z0-9._-]+)(?:@([A-Za-z0-9._-]+))?\s*(.*)$", line)
                if m and m.group(1).lower() not in ("no", "run", "name", "plugin"):
                    name, mp = m.group(1), m.group(2)
                    add(
                        id=f"{name}@{mp}" if mp else name,
                        name=name,
                        marketplace=mp,
                        status="installed",
                        version=None,
                        raw=line.strip() if m.group(3) else None,
                    )
    elif host == "codex":
        # non-JSON fallback: leave raw lines
        for line in lines:
            if line.strip():
                add(id=None, name=None, marketplace=None, status="unknown", raw=line.rstrip())
except Exception:
    out = []
    for line in lines:
        if line.strip():
            add(id=None, name=None, marketplace=None, status="unknown", raw=line.rstrip())

if q:
    ql = q.lower()
    filtered = []
    for p in out:
        hay = " ".join(
            str(p.get(k) or "") for k in ("id", "name", "marketplace", "raw")
        ).lower()
        if ql in hay:
            filtered.append(p)
    out = filtered

print(json.dumps(out, ensure_ascii=False))
PY
}

# ---------------------------------------------------------------------------
# marketplaces list / add / update
# ---------------------------------------------------------------------------
cmd_marketplaces_list() {
  local host bin
  local -a all_items=()
  local any_ok=0

  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude)
        # Prefer --json when supported; fall back to human list.
        run_host_cmd 0 "$bin" plugin marketplace list --json
        if [[ "$LAST_EC" -ne 0 ]]; then
          run_host_cmd 0 "$bin" plugin marketplace list
        fi
        ;;
      codex)  run_host_cmd 0 "$bin" plugin marketplace list ;;
      grok)   run_host_cmd 0 "$bin" plugin marketplace list ;;
    esac
    note_host_result "$host" "marketplaces list" "$LAST_EC"
    if [[ "$LAST_EC" -eq 0 ]]; then
      any_ok=1
      local parsed
      parsed="$(parse_marketplaces "$host" "$LAST_STDOUT")"
      while IFS= read -r line; do
        [[ -n "$line" ]] && all_items+=("$line")
      done < <(python3 -c 'import json,sys; [print(json.dumps(x,ensure_ascii=False)) for x in json.loads(sys.stdin.read())]' <<<"$parsed")
    else
      all_items+=("$(python3 -c 'import json,sys; print(json.dumps({"host":sys.argv[1],"name":None,"raw":sys.argv[2],"error":True},ensure_ascii=False))' "$host" "${LAST_STDERR:-$LAST_STDOUT}")")
    fi
  done

  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi

  if [[ "$JSON_OUT" -eq 1 ]]; then
    python3 -c '
import json,sys
items=[json.loads(l) for l in sys.stdin if l.strip()]
print(json.dumps({"marketplaces": items}, indent=2, ensure_ascii=False))
' <<<"$(printf '%s\n' "${all_items[@]+"${all_items[@]}"}")"
  else
    printf '%-8s %-32s %s\n' "HOST" "NAME" "SOURCE"
    for item in "${all_items[@]+"${all_items[@]}"}"; do
      python3 -c '
import json,sys
r=json.loads(sys.argv[1])
name=r.get("name") or (r.get("raw") or "-")[:40]
src=r.get("source") or ""
print("%-8s %-32s %s" % (r.get("host","?"), name, src))
' "$item"
    done
  fi

  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

cmd_marketplaces_add() {
  local src="${1:-}"
  if [[ -z "$src" ]]; then
    printf 'Usage: marketplaces add <src>\n' >&2
    exit 2
  fi
  local host bin
  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude) run_host_cmd "$DRY_RUN" "$bin" plugin marketplace add "$src" ;;
      codex)  run_host_cmd "$DRY_RUN" "$bin" plugin marketplace add "$src" ;;
      grok)   run_host_cmd "$DRY_RUN" "$bin" plugin marketplace add "$src" ;;
    esac
    note_host_result "$host" "marketplaces add" "$LAST_EC"
    if [[ "$DRY_RUN" -eq 0 && -n "$LAST_STDOUT" ]]; then
      printf '[%s] %s\n' "$host" "$LAST_STDOUT"
    fi
  done
  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi
  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

cmd_marketplaces_update() {
  local name="${1:-}"
  local host bin
  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude)
        if [[ -n "$name" ]]; then
          run_host_cmd "$DRY_RUN" "$bin" plugin marketplace update "$name"
        else
          run_host_cmd "$DRY_RUN" "$bin" plugin marketplace update
        fi
        ;;
      codex)
        # Codex uses `upgrade` for marketplaces (refresh snapshots)
        run_host_cmd "$DRY_RUN" "$bin" plugin marketplace upgrade
        ;;
      grok)
        if [[ -n "$name" ]]; then
          run_host_cmd "$DRY_RUN" "$bin" plugin marketplace update "$name"
        else
          run_host_cmd "$DRY_RUN" "$bin" plugin marketplace update
        fi
        ;;
    esac
    note_host_result "$host" "marketplaces update" "$LAST_EC"
    if [[ "$DRY_RUN" -eq 0 && -n "$LAST_STDOUT" ]]; then
      printf '[%s] %s\n' "$host" "$LAST_STDOUT"
    fi
  done
  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi
  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

# ---------------------------------------------------------------------------
# plugins list / install / uninstall / update
# ---------------------------------------------------------------------------
cmd_plugins_list() {
  local host bin
  local -a all_items=()

  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude)
        # Prefer --json (like codex); fall back to human when unsupported.
        run_host_cmd 0 "$bin" plugin list --json
        if [[ "$LAST_EC" -ne 0 ]]; then
          run_host_cmd 0 "$bin" plugin list
        fi
        ;;
      codex)  run_host_cmd 0 "$bin" plugin list --json ;;
      grok)
        # Prefer --json when supported; fall back to human
        run_host_cmd 0 "$bin" plugin list --json
        if [[ "$LAST_EC" -ne 0 ]]; then
          run_host_cmd 0 "$bin" plugin list
        fi
        ;;
    esac
    note_host_result "$host" "plugins list" "$LAST_EC"
    if [[ "$LAST_EC" -eq 0 ]]; then
      local parsed
      parsed="$(parse_plugins "$host" "$LAST_STDOUT" "$PLUGIN_Q")"
      while IFS= read -r line; do
        [[ -n "$line" ]] && all_items+=("$line")
      done < <(python3 -c 'import json,sys; [print(json.dumps(x,ensure_ascii=False)) for x in json.loads(sys.stdin.read())]' <<<"$parsed")
    fi
  done

  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi

  if [[ "$JSON_OUT" -eq 1 ]]; then
    python3 -c '
import json,sys
items=[json.loads(l) for l in sys.stdin if l.strip()]
print(json.dumps({"plugins": items}, indent=2, ensure_ascii=False))
' <<<"$(printf '%s\n' "${all_items[@]+"${all_items[@]}"}")"
  else
    printf '%-8s %-40s %-24s %-12s %s\n' "HOST" "ID" "NAME" "STATUS" "VERSION"
    for item in "${all_items[@]+"${all_items[@]}"}"; do
      python3 -c '
import json,sys
r=json.loads(sys.argv[1])
print("%-8s %-40s %-24s %-12s %s" % (
  r.get("host","?"),
  (r.get("id") or r.get("raw") or "-")[:40],
  (r.get("name") or "-")[:24],
  (r.get("status") or "-")[:12],
  r.get("version") or "",
))
' "$item"
    done
  fi

  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

cmd_plugins_install() {
  local id="${1:-}"
  if [[ -z "$id" ]]; then
    printf 'Usage: plugins install <id>\n' >&2
    exit 2
  fi
  local host bin
  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude)
        # dry-run: print would-run, do not exec
        run_host_cmd "$DRY_RUN" "$bin" plugin install "$id"
        note_host_result "$host" "plugins install" "$LAST_EC"
        ;;
      codex)
        if [[ "$id" != *@* ]]; then
          printf 'marketplace-run: codex requires name@marketplace (got %q)\n' "$id" >&2
          ANY_HOST_FAILED=1
          HAD_AVAILABLE_HOST=1
          PRECONDITION_FAILED=1
          continue
        fi
        run_host_cmd "$DRY_RUN" "$bin" plugin add "$id"
        note_host_result "$host" "plugins install" "$LAST_EC"
        ;;
      grok)
        # Grok accepts git URL / GitHub shorthand / local path only.
        # Claude-style name@marketplace is rejected: @ means git ref on Grok, not marketplace.
        if is_claude_style_marketplace_id "$id"; then
          printf 'marketplace-run: grok does not accept Claude-style marketplace ids (%q).\n' "$id" >&2
          printf '  Grok accepts git URL, GitHub shorthand (user/repo or user/repo@ref), or a local path only.\n' >&2
          printf '  On Grok, @ is a git ref — not a marketplace selector. Use install-local for skill-dir side-load,\n' >&2
          printf '  or install via Claude/Codex for name@marketplace plugins.\n' >&2
          ANY_HOST_FAILED=1
          HAD_AVAILABLE_HOST=1
          PRECONDITION_FAILED=1
          continue
        fi
        run_host_cmd "$DRY_RUN" "$bin" plugin install "$id"
        note_host_result "$host" "plugins install" "$LAST_EC"
        ;;
    esac
    if [[ "$DRY_RUN" -eq 0 && -n "${LAST_STDOUT:-}" ]]; then
      printf '[%s] %s\n' "$host" "$LAST_STDOUT"
    fi
  done
  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi
  # Host preconditions (Codex bare name, Grok Claude-style id): exit 4 when that was the only host.
  if [[ "$ANY_HOST_FAILED" -ne 0 ]]; then
    if [[ "$PRECONDITION_FAILED" -eq 1 && "${#SELECTED_HOSTS[@]}" -eq 1 ]]; then
      exit 4
    fi
    exit 1
  fi
}

cmd_plugins_uninstall() {
  local id="${1:-}"
  if [[ -z "$id" ]]; then
    printf 'Usage: plugins uninstall <id>\n' >&2
    exit 2
  fi
  local host bin
  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude) run_host_cmd "$DRY_RUN" "$bin" plugin uninstall "$id" ;;
      codex)  run_host_cmd "$DRY_RUN" "$bin" plugin remove "$id" ;;
      grok)   run_host_cmd "$DRY_RUN" "$bin" plugin uninstall "$id" ;;
    esac
    note_host_result "$host" "plugins uninstall" "$LAST_EC"
    if [[ "$DRY_RUN" -eq 0 && -n "$LAST_STDOUT" ]]; then
      printf '[%s] %s\n' "$host" "$LAST_STDOUT"
    fi
  done
  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi
  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

cmd_plugins_update() {
  local id="${1:-}"
  local host bin
  for host in "${SELECTED_HOSTS[@]}"; do
    if ! host_is_available "$host"; then
      skip_unavailable "$host"
      continue
    fi
    bin="$(resolve_bin "$host")"
    case "$host" in
      claude)
        if [[ -n "$id" ]]; then
          run_host_cmd "$DRY_RUN" "$bin" plugin update "$id"
        else
          # Claude requires a plugin arg; update marketplaces instead is wrong.
          # Skip with note when no id.
          printf 'marketplace-run: claude plugins update requires <id> (skipped)\n' >&2
          HAD_AVAILABLE_HOST=1
          continue
        fi
        ;;
      codex)
        # Codex has no per-plugin update; marketplace upgrade refreshes snapshots
        run_host_cmd "$DRY_RUN" "$bin" plugin marketplace upgrade
        ;;
      grok)
        if [[ -n "$id" ]]; then
          run_host_cmd "$DRY_RUN" "$bin" plugin update "$id"
        else
          run_host_cmd "$DRY_RUN" "$bin" plugin update
        fi
        ;;
    esac
    note_host_result "$host" "plugins update" "$LAST_EC"
    if [[ "$DRY_RUN" -eq 0 && -n "${LAST_STDOUT:-}" ]]; then
      printf '[%s] %s\n' "$host" "$LAST_STDOUT"
    fi
  done
  if [[ "$HAD_AVAILABLE_HOST" -eq 0 ]]; then
    printf 'marketplace-run: no selected host available\n' >&2
    exit 3
  fi
  [[ "$ANY_HOST_FAILED" -eq 0 ]] || exit 1
}

# ---------------------------------------------------------------------------
# install-local → repo install.sh (skill-dir side-load, not marketplace)
# ---------------------------------------------------------------------------
cmd_install_local() {
  local install_sh="${MARKETPLACE_INSTALL_SH:-}"
  if [[ -z "$install_sh" ]]; then
    if [[ -z "$repo_dir" ]]; then
      printf 'marketplace-run: could not locate install.sh (walked up from %s; set MARKETPLACE_INSTALL_SH)\n' "$script_dir" >&2
      exit 2
    fi
    install_sh="$repo_dir/install.sh"
  fi
  if [[ ! -f "$install_sh" ]]; then
    printf 'marketplace-run: install.sh not found at %s\n' "$install_sh" >&2
    exit 2
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'would-run: %s %s\n' "$install_sh" "$*"
    exit 0
  fi
  exec bash "$install_sh" "$@"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
case "$verb1" in
  hosts)
    cmd_hosts
    exit 0
    ;;
  marketplaces)
    case "$verb2" in
      list)
        shift 2 || shift 1
        cmd_marketplaces_list
        ;;
      add)
        shift 2
        cmd_marketplaces_add "${1:-}"
        ;;
      update)
        shift 2 || true
        cmd_marketplaces_update "${1:-}"
        ;;
      *)
        printf 'Unknown marketplaces subcommand: %s\n' "${verb2:-}" >&2
        usage
        exit 2
        ;;
    esac
    ;;
  plugins)
    case "$verb2" in
      list)
        shift 2 || shift 1
        # --q may have been global-parsed already
        cmd_plugins_list
        ;;
      install)
        shift 2
        cmd_plugins_install "${1:-}"
        ;;
      uninstall)
        shift 2
        cmd_plugins_uninstall "${1:-}"
        ;;
      update)
        shift 2 || true
        cmd_plugins_update "${1:-}"
        ;;
      *)
        printf 'Unknown plugins subcommand: %s\n' "${verb2:-}" >&2
        usage
        exit 2
        ;;
    esac
    ;;
  install-local)
    shift
    cmd_install_local "$@"
    ;;
  *)
    printf 'Unknown verb: %s\n' "$verb1" >&2
    usage
    exit 2
    ;;
esac
