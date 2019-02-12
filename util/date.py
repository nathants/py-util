import datetime

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)

def format(dt):
    return dt.isoformat() + 'Z'

def parse(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
