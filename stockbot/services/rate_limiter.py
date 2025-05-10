import time
from collections import deque
from stockbot.config import RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_CALLS

USER_CALL_LOGS = {}  # user_id -> deque of timestamps

def is_rate_limited(user_id):
    """Returns True if user exceeded RATE_LIMIT_MAX_CALLS in the last RATE_LIMIT_WINDOW seconds."""
    now = time.time()
    dq = USER_CALL_LOGS.setdefault(user_id, deque())
    # prune old timestamps
    while dq and dq[0] <= now - RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_MAX_CALLS:
        return True
    dq.append(now)
    return False
