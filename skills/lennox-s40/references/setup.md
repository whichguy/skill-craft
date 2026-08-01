# Setup — lennox-s40

## One-time

```sh
# From skill package root (skill-craft clone or installed leaf)
bash scripts/lennox-s40 --setup

# Discover S40 on LAN (mDNS + Connect probe)
bash scripts/lennox-s40 discover
export LENNOX_IP=<printed-ip>

# Optional: reserve DHCP for the thermostat MAC on your router
```

## Requirements

- macOS or Linux on the **same network** as the S40 (guest/IoT isolation breaks local API)
- Python 3.10+
- Outbound HTTPS to thermostat IP port **443** (self-signed cert; client disables verify)
- Package: [lennoxs30api](https://github.com/PeteRager/lennoxs30api) (installed by `--setup`)

## S40 notes

| Item | Detail |
|------|--------|
| Local API | HTTPS `/Endpoints/<app_id>/Connect` → 204 |
| Cloud | Not used (S40 community cloud path unsupported) |
| Firmware | Prefer ≥ 04.25.0070 if Connect fails |
| app_id | Unique per client; colliding ids steal the message queue |
| Multi-zone | `--zone Name` or `--zone 0` |

## Security

- Prefer a unique `LENNOX_APP_ID` for this skill vs the phone app.
- Do not log raw `interfaces` payloads (may include network credentials).
- Keep control on a trusted LAN; this is unauthenticated local control by design.
