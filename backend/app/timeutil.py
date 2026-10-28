from datetime import UTC, datetime


def utcnow() -> datetime:
    """Naive UTC timestamp: the database columns store naive UTC values."""
    return datetime.now(UTC).replace(tzinfo=None)
