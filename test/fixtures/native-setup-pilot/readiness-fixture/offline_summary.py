"""A deliberately rough offline summary formatter for independent work."""


def render_summary(rows: list[dict[str, str]]) -> str:
    """Render local readiness rows; this path must not read or mutate setup state."""
    return "\n".join(f" {row['target']}   : {row['status']} " for row in rows) + "\n"
