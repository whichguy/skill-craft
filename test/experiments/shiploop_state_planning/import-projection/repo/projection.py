def for_reader(record, reader_version):
    if record["state"] != "projecting":
        raise ValueError("only a projecting import can produce a projection")

    payload = {
        "import_id": record["id"],
        "source_revision": record["revision"],
        "rows": record["rows"],
    }
    if reader_version == 1:
        return payload
    if reader_version == 2:
        return {**payload, "summary": list(record["summary"])}
    raise ValueError("unknown reader version")

