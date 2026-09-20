"""Remote ReviewRequest.status is the durable status owner; this worker only polls it."""


def refresh_pending_reviews(remote, request_ids):
    return [remote.read_review_request(request_id)["status"] for request_id in request_ids]
