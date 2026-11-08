"""Reference implementation for R-1, kept outside the native subject corpus."""


def render_summary(rows: list[dict[str, str]]) -> str:
    return "".join(f"{row['target']}: {row['status']}\n" for row in rows)
