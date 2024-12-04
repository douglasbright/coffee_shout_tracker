from datetime import datetime, timedelta

def time_since(dt):
    now = datetime.utcnow()
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days} days"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes"
    else:
        return "just now"