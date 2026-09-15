# Immutable server-port contract

`config.server_port(env)` reads only the optional `APP_PORT` setting. If absent,
it returns 8080. When present, it must be an ASCII decimal string representing
an integer from 1 through 65535; `None`, whitespace, signs, non-strings, and
out-of-range values raise `ValueError`. The unrelated `PORT` key is ignored.
