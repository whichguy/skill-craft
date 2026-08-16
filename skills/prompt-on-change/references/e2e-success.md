# prompt-on-change — e2e success contract

This is the live verification card for session-aware delivery (2.2.0).
The runner is `test/prompt-on-change-e2e.test.sh`. A passing run writes
`report/SUCCESS.md` and `report/scorecard.json` under `POC_GROK_KEEP`
(or prints the same markdown to stdout).

Discovery (skill installed) is not this card. Success is tokens on stdout
plus a scorecard row.

## How to run

```sh
# Live card (default): real Grok --to + time.is all-group + lifecycle-to.
# Throwaway uuids. Do not point --to at an open TUI.
unset GROK_BIN
POC_GROK_KEEP=/tmp/poc-e2e-keep/suite \
  bash test/prompt-on-change-e2e.test.sh

# Offline only (local HTTP, no Grok, no public web). Hermetic suite pins this.
POC_E2E=0 bash test/prompt-on-change-e2e.test.sh
```

Subset: `POC_E2E_CASES=offline,local-to,external-multi,lifecycle-to`.  
Live site URL: `POC_LIVE_SITE_URL` (default `https://time.is/Los_Angeles`).  
Do **not** point `--to` at an open TUI uuid. Resume uses `--assume-idle`.
Public-surface inventory: `references/coverage-matrix.md`.

## Cases

| Case | Network | Grok | What success looks like |
|------|---------|------|-------------------------|
| `offline-local-multi` | 127.0.0.1 | no | seed → one empty poll → two `LLM_ESCALATION:` (`price_changed`, `status_changed`) → **one** `PROMPT_ISSUED:` containing both. No `PROMPT_RUN`. |
| `live-local-to` | 127.0.0.1 | yes | same two-condition poll with `--to grok:<uuid>` → `PROMPT_RUN:` then `issue --evidence` ×2 → `PROMPT_RESUME:` and `event.prompt.md`. |
| `live-external-multi` | time.is | yes | silent polls until `#clock` enters the next minute; `all:` of `time_hits_known`, `clock_moved`, `page_ok`, `has_date` → **four** escalations, **one** issue, `PROMPT_RUN:` then resume. |
| `lifecycle-to` | 127.0.0.1 | yes | explain → seed → silent → `--to` match → fire_once silent → status → claim → `issue --last --to` resume. Refuse / `--force-new` / isolated `--exec` stay on delivery + grok-native. |

Skipped live rows (`SKIP`) are success only when `POC_E2E=0` (hermetic pin). A bare invoke is live and `FAIL`s if Grok or time.is cannot complete. `FAIL` fails the script.

## Tokens (normative)

| Token | Meaning |
|-------|---------|
| `SEED_OK:` | First poll recorded a baseline. |
| (empty stdout, exit 0) | No-change poll. |
| `LLM_ESCALATION: <path>` | One evidence file per matched condition **this poll**. |
| `PROMPT_ISSUED: <path>` | One filled prompt for this poll’s `condition_matched` set. |
| `PROMPT_RUN:` | New Grok session (`--session-id`). |
| `PROMPT_RESUME:` | Existing idle Grok session (`--resume`). |

Grok must not fetch the watched URL. Outcome fence `json outcome` is the log contract.
If a model still `mv`s evidence into `processed/`, the suite resolves that path
and resumes from there (at-least-once; same as `issue --last`).

## Proven live (2026-08-16)

Manual card before this suite existed, kept under `/tmp/poc-e2e-keep/`:

- Isolated `--exec`: clock `15:00` → `16:53`, Grok 15.4s, exit 0.
- `--to` local price: `100` → `40`, `PROMPT_RUN` 6.7s then `PROMPT_RESUME` 2.4s.
- time.is single condition: 3 silent polls, `07:00:54PM` → `07:01:03PM`.
- time.is `--to`: 3 silent polls, `07:04:59PM` → `07:05:07PM`, then resume.
- time.is **all-group of four**: 2 silent polls, four escalations at `07:12:07PM`, one issue, Grok named all four ids, then resume.

Re-run the e2e script (live by default) to refresh `SUCCESS.md` instead of treating those dirs as SoT.
