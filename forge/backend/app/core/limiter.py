import time
from app.core import state

def is_rate_limited(ip: str, action: str = "quiz", limit: int = 3, period: int = 60) -> bool:
    """
    Check if an IP address has exceeded the rate limit for a specific action.
    
    Args:
        ip: The client's IP address.
        action: The name of the action (e.g., "quiz", "room").
        limit: Maximum number of requests allowed in the period.
        period: The time window in seconds.
        
    Returns:
        True if the IP is rate limited, False if allowed.
    """
    now = time.time()
    key = f"{action}:{ip}"
    
    # Initialize record for this key if not present
    if key not in state.quiz_rate_limits:
        state.quiz_rate_limits[key] = []
    
    # Clean up old timestamps outside the current window
    state.quiz_rate_limits[key] = [
        ts for ts in state.quiz_rate_limits[key] 
        if now - ts < period
    ]
    
    # Check if we are over the limit
    if len(state.quiz_rate_limits[key]) >= limit:
        return True
    
    # Not limited, so record this new request
    state.quiz_rate_limits[key].append(now)
    return False
