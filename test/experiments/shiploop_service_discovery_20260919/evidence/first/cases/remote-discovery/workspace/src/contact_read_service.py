"""The runtime adapter always uses the app CRM service account."""


class ContactReadService:
    def __init__(self, cache, runtime):
        self.cache, self.runtime = cache, runtime

    def list_contacts(self, query):
        cached = self.cache.get(query)
        if cached is not None:
            return cached
        rows = self.runtime.query_contacts(query)
        self.cache.put(query, rows, ttl_seconds=600)
        return rows
