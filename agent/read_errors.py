"""Failures shared by Recorded-page readers and the Comment pass."""


class PostPageUnavailable(RuntimeError):
    """A Post's page no longer loads and its tracking record should be closed."""
