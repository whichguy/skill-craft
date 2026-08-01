---
name: lennox-s40
description: >-
  Control a Lennox S40 (and S30/E30 LAN) smart thermostat over the local network:
  read status, set mode/setpoints/fan/away. Use when the user mentions home AC,
  heat, thermostat, Lennox Home, S40 zones, or HVAC setpoints. Local HTTPS only
  (no Lennox cloud). Requires LAN reachability and one-time scripts/lennox-s40 --setup.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: smart-home
    tags:
      - lennox
      - s40
      - thermostat
      - hvac
      - smart-home
      - local-api
---

# lennox-s40

**Script-backed** skill for local LAN control of Lennox **S40** (also S30/E30 local).
Uses the community reverse-engineered API ([lennoxs30api](https://github.com/PeteRager/lennoxs30api)).
No cloud password. No baked-in home IP — set `LENNOX_IP` after `discover`.

## When to use

- Read or change home HVAC temperature, mode, fan, or away on a Lennox S40
- “What’s the thermostat at?” / “Set downstairs cool to 76”
- Debug local connectivity to the S40

## When not to use

- Other HVAC brands (use their integrations)
- Controlling devices you do not own / non-local networks
- Expecting Lennox cloud-only M30 path without local API

## Procedure

1. **One-time deps:** `bash scripts/lennox-s40 --setup`
2. **Find unit:** `bash scripts/lennox-s40 discover` → `export LENNOX_IP=…`
3. **Read:** `bash scripts/lennox-s40 status`
4. **Write** (optional): mode / cool / heat / fan / away with `--zone` as needed
5. Prefer re-read `status` after writes if the user wants confirmation

## CLI contract

```sh
# Package-relative (preferred)
bash scripts/lennox-s40 --setup
bash scripts/lennox-s40 discover
bash scripts/lennox-s40 --ip "$LENNOX_IP" status
bash scripts/lennox-s40 mode cool --zone Downstairs
bash scripts/lennox-s40 cool 76 --zone Downstairs
bash scripts/lennox-s40 heat 68 --zone Upstairs
bash scripts/lennox-s40 fan auto --zone 0
bash scripts/lennox-s40 away off
```

| Command | Effect |
|---------|--------|
| `discover` | mDNS + Connect probe; prints `export LENNOX_IP=…` on success |
| `status` | JSON: system + zones (temp, humidity, setpoints, mode, fan) |
| `mode <off\|cool\|heat\|auto>` | HVAC mode (`auto` → Lennox `heat and cool`) |
| `cool <F>` / `heat <F>` | Setpoint publish |
| `fan <auto\|on\|circulate>` | Fan mode |
| `away <on\|off>` | Manual away |

Exit codes: `0` ok · `1` soft failure (discover miss) · `2` missing deps / config.

Env: `LENNOX_IP`, `LENNOX_APP_ID`, `LENNOX_VENV`, `LENNOX_PYTHON`, `LENNOX_TIMEOUT`.

## Protocol (local)

```text
POST https://<ip>/Endpoints/<app_id>/Connect     → 204
POST https://<ip>/Messages/RequestData
GET  https://<ip>/Messages/<app_id>/Retrieve     (long-poll)
POST https://<ip>/Messages/Publish
```

Self-signed TLS (`CN=Lennox`). No Authorization header on LAN.

## Install (skill-craft)

```sh
# skill-dir — all hosts (Hermes = materialized copy under software-development/)
./install.sh --skill lennox-s40

# Claude plugin (after skill-craft-market pin + skill-craft publish)
# claude plugin install lennox-s40@skill-craft-market
```

See [references/host-matrix.md](references/host-matrix.md) and [references/setup.md](references/setup.md).

## Upstream

- Python API: https://github.com/PeteRager/lennoxs30api  
- Home Assistant: https://github.com/PeteRager/lennoxs30  
- TypeScript: https://github.com/lukealonso/lennoxapi  
