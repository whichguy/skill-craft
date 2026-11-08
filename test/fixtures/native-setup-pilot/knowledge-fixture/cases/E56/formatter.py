"""Format already-validated readiness rows without reading or changing target state."""


def render_summary(rows):
    """Return one '<target>: <status>\n' line per row, or '' for no rows.

    The caller validates a list of mappings whose target/status values are
    strings. This pure formatter has no external state or error recovery.
    """
    return "".join(f"{row['target']}: {row['status']}\n" for row in rows)
