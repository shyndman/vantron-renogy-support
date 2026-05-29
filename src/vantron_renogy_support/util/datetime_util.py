from datetime import datetime, timedelta


def seconds_ago(seconds: int | float, ts: datetime | None = None) -> datetime:
    if ts is None:
        ts = datetime.now()
    return ts - timedelta(seconds=seconds, microseconds=ts.microsecond)
