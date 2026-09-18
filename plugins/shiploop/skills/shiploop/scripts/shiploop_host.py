"""Shared failure type for ShipLoop's optional supervised host sessions."""


class HostError(RuntimeError):
    """The host could not complete an owner; automatic replay is unsafe."""
