def clean_lines(text):
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return [line.strip() for line in text.splitlines() if line.strip()]
