from datetime import datetime, timedelta

def seconds_ago(seconds, ts=datetime.now()):
    return ts - timedelta(seconds=seconds, microseconds=ts.microsecond)
