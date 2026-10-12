from fastapi import HTTPException, status, Request
from typing import Dict
from datetime import datetime, timedelta
import threading


class RateLimiter:
    """Simple in-memory rate limiter for development."""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed within rate limit."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        with self.lock:
            if key not in self.requests:
                self.requests[key] = []
            
            # Remove old requests outside the window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
            
            # Check if under limit
            if len(self.requests[key]) >= max_requests:
                return False
            
            # Add current request
            self.requests[key].append(now)
            return True
    
    def cleanup_old_keys(self, max_age_seconds: int = 3600):
        """Clean up old keys to prevent memory leaks."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=max_age_seconds)
        
        with self.lock:
            keys_to_remove = []
            for key, timestamps in self.requests.items():
                if not timestamps or max(timestamps) < cutoff:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def RateLimitDependency(max_requests: int = 5, window_seconds: int = 60):
    """FastAPI dependency factory for rate limiting."""
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        
        if not rate_limiter.is_allowed(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please try again in {window_seconds} seconds."
            )
    
    return dependency
