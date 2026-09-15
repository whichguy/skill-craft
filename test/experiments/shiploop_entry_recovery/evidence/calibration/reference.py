def clean_lines(text):
    if not isinstance(text, str):
        raise TypeError('text must be str')
    return [line for raw in text.splitlines() if (line := raw.strip())]
