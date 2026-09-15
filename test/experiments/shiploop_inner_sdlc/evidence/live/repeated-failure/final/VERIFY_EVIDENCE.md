# Verification evidence

## Initial claim and failing check

`STALE_DIAGNOSTIC.md` claimed that an import cache or temporary environment
retry might explain the failure. It was treated as historical context rather
than evidence. Before changing the fixture, `python3 -B -m unittest -v
test_config.py` failed `test_app_port_is_used`: `server_port({'APP_PORT':
'9001'})` returned `8080` instead of `9001`.

## Discriminating observation

Before the correction, a direct process-local call printed
`{'APP_PORT_9001': 8080, 'PORT_9001': 9001}`. The result was deterministic in
a fresh Python process and distinguished a key-selection defect from the stale
cache/environment claim.

## Revised cause and correction

The source selected the unrelated `PORT` key. It also used `env.get(...)` and
therefore would have treated an explicitly present `APP_PORT: None` the same
as an absent setting, contrary to the immutable contract. `config.server_port`
now checks for the presence of `APP_PORT`, defaults only when that key is
absent, and validates every present value as an ASCII decimal port in the
allowed range. `PORT` is ignored.

## Current checks

After the correction, `python3 -B -m unittest -v test_config.py` passed all
four tests. They cover a normal `APP_PORT`, absence and `PORT`-only inputs,
accepted bounds and leading zeroes, and rejected `None`, whitespace, signs,
non-strings, non-ASCII digits, and out-of-range values.
