def slugify(title):
    if not isinstance(title, str):
        raise ValueError("title")
    return title.strip().lower().replace(" ", "-")
