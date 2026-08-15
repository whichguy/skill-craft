# Flight Enrichment Pattern — Proven End-to-End

This reference captures the proven pattern for monitoring airline flights with the `prompt-on-change` detect engine. The config at `configs/as706_flight_enriched.yaml` was dry-run tested against live Alaska SSR data and successfully extracted all 13 fields, fired 3 actions, and produced the "Original schedule" enrichment Jim requested.

**For new flights:** copy `configs/templates/flight_template.yaml`, fill in the placeholders (FLIGHT_NUMBER, FLIGHT_DATE, AIRLINE_NAME, AIRLINE_URL, FLIGHT_EVENT_ID, UBER_EVENT_ID, UBER_OFFSET_MIN, TIMEZONE, EXPIRES), and drop in `configs/`. The template is airline-agnostic — any airline with a JSON-LD status page works.

## What It Extracts (13 fields from Alaska SSR JSON-LD)

| Field | JSONPath | Example |
|-------|----------|---------|
| `dep_time` | `$.departureTime` | `2026-07-07T17:20:00-07:00` |
| `arr_time` | `$.arrivalTime` | `2026-07-07T19:18:00-07:00` |
| `scheduled_dep` | `$.scheduledDepartureTime` | `2026-07-07T17:25:00-07:00` |
| `scheduled_arr` | `$.scheduledArrivalTime` | `2026-07-07T19:33:00-07:00` |
| `dep_gate` | `$.departureGate` | `C10` |
| `arr_gate` | `$.arrivalGate` | `8` |
| `baggage` | `$.baggageCarousel` | `3` |
| `aircraft` | `$.aircraft.tailNumber` | `N293AK` |
| `boarding` | `$.boardingTime` | `4:50 pm` |
| `status` | `$.flightStatus` | `On time` |
| `duration` | `$.duration` | `PT1H58M` |
| `dep_airport` | `$.departureAirport.iataCode` | `SEA` |
| `arr_airport` | `$.arrivalAirport.iataCode` | `OAK` |

## Condition Groups

```yaml
groups:
  - name: time_changed
    any: [dep_time_changed, arr_time_changed]
    actions: [patch_flight, patch_uber]
  - name: gate_changed
    any: [dep_gate_changed, arr_gate_changed]
    actions: [patch_flight_gate]
  - name: status_changed
    any: [status_delayed, status_cancelled]
    actions: [patch_flight, patch_uber]
  - name: critical
    any: [status_cancelled]
    actions: [patch_flight]
```

## Actions

```yaml
actions:
  patch_flight:
    type: calendar_patch
    event_id: {from_state: flight_event_id, required: true}
    fields:
      summary: "AS706: {{ dep_airport }} → {{ arr_airport }} — {{ status }}"
      start: {dateTime: "{{ dep_time }}", timeZone: "TIMEZONE"}
      end: {dateTime: "{{ arr_time }}", timeZone: "TIMEZONE"}
      description: |
        ✈️ **Alaska Airlines 706**
        {{ dep_airport }} → {{ arr_airport }}
        {{ dep_time | fmt_time }} → {{ arr_time | fmt_time }} ({{ duration }})

        Original schedule: Depart {{ scheduled_dep | fmt_time }} → Arrive {{ scheduled_arr | fmt_time }}

        🛫 Gate {{ dep_gate }} · Boarding {{ boarding }}
        🛬 Gate {{ arr_gate }} · Baggage Carousel {{ baggage }}
        ✈️ {{ aircraft }}

        Status: {{ status }}
        [Live Status](https://www.alaskaair.com/status/706/2026-07-07)

  patch_uber:
    type: calendar_patch
    event_id: {from_state: uber_event_id, required: true}
    computed:
      uber_pickup: "{{ arr_time | add_minutes: 17 }}"
      uber_end: "{{ uber_pickup | add_minutes: 48 }}"
    fields:
      summary: "🚗 Uber: {{ arr_airport }} → Home"
      start: {dateTime: "{{ uber_pickup }}", timeZone: "TIMEZONE"}
      end: {dateTime: "{{ uber_end }}", timeZone: "TIMEZONE"}
      description: |
        🚗 Uber pickup at {{ arr_airport }}
        Arrival: {{ arr_time | fmt_time }}
        Pickup: {{ uber_pickup | fmt_time }} (arrival + 17 min)
        Duration: ~48 min

  patch_flight_gate:
    type: calendar_patch
    event_id: {from_state: flight_event_id, required: true}
    fields:
      description: |
        ✈️ **Alaska Airlines 706**
        {{ dep_airport }} → {{ arr_airport }}
        {{ dep_time | fmt_time }} → {{ arr_time | fmt_time }} ({{ duration }})

        Original schedule: Depart {{ scheduled_dep | fmt_time }} → Arrive {{ scheduled_arr | fmt_time }}

        🛫 Gate {{ dep_gate }} · Boarding {{ boarding }}
        🛬 Gate {{ arr_gate }} · Baggage Carousel {{ baggage }}
        ✈️ {{ aircraft }}

        Status: {{ status }}
        [Live Status](https://www.alaskaair.com/status/706/2026-07-07)
```

## Key Design Decisions

1. **`scheduled_dep`/`scheduled_arr` are the booked times** — distinct from `dep_time`/`arr_time` (live times). This is what enables the "Original schedule" enrichment. The Alaska SSR JSON-LD provides both.

2. **Three separate action groups** — `time_changed` patches both flight + Uber, `gate_changed` patches only the flight description (no time change), `critical` patches flight + escalates to LLM. This avoids unnecessary Uber patches on gate-only changes.

3. **`computed` for Uber offset** — `uber_pickup = arr_time + 17 min`, `uber_end = uber_pickup + 48 min`. The `add_minutes` filter handles datetime arithmetic in templates.

4. **`unless:` on status conditions** — prevents re-patching when the calendar already shows the status (e.g., `cal_title contains "DELAYED"`).

5. **`fire_once: true`** — suppresses re-escalation for the same value. The acknowledged dict stores `{at: timestamp, value: "..."}`.

## Dry-Run Verification

```bash
# Validate
/opt/data/.venv-sync/bin/python scripts/detect_engine.py \
  --config configs/as706_flight_enriched.yaml --validate

# Dry run (fetch + evaluate, no actions)
/opt/data/.venv-sync/bin/python scripts/detect_engine.py \
  --config configs/as706_flight_enriched.yaml --dry-run
```

The dry run against the live Alaska Airlines page successfully:
- Extracted all 13 fields
- Fired 3 actions: `patch_flight`, `patch_uber`, `patch_flight_gate`
- Description included: `Original schedule: Depart 5:25 pm → Arrive 7:33 pm`

## Migration from `calendar-sync-trigger`

| Old (`calendar_sync.py`) | New (guard engine) |
|--------------------------|---------------------|
| `sources: [{type: flight_status}]` | `sources: [{url: alaskaair.com/status/...}]` |
| `conditions: [{field, op, actions}]` | `conditions: [...]` + `groups: [{any/all, actions}]` |
| `calendar_events: {flight: {event_id}}` | `actions: {patch_flight: {event_id}}` |
| `cleanup: {stale_events: [...]}` | `actions: {delete_stale: {type: calendar_delete}}` |
| No state management | Anti-bounce state with `fire_once`/`refire_after` |
| No LLM escalation | `llm_escalation` with full evidence payloads |
| No `computed` variables | `computed:` for derived values like `uber_pickup` |
