"""Rate limiting for external API calls.

Implements fixed-window counter to respect API rate limits:
- Serper API: 100 calls/day
- Instagram scraping: 5 profiles/minute (terms of service)
- TikTok scraping: 3 profiles/minute (terms of service)
- LinkedIn circuit breaker: Already implemented in enrichment_tasks.py
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Fixed-window counter rate limiter."""
    
    # Default rate limits (requests/period)
    DEFAULT_LIMITS = {
        "serper": {"limit": 100, "window": 3600 * 24},  # 100 per day
        "instagram": {"limit": 5, "window": 60},  # 5 per minute
        "tiktok": {"limit": 3, "window": 60},  # 3 per minute
        "twitter": {"limit": 15, "window": 900},  # 15 per 15 min (standard Twitter v2)
        "github": {"limit": 60, "window": 3600},  # 60 per hour (public API)
        "linkedin": {"limit": 10, "window": 3600},  # Circuit breaker implements per-IP, this is fallback
    }
    
    def __init__(self, limits: Optional[Dict] = None):
        """Initialize rate limiter.
        
        Args:
            limits: Dict of {service: {"limit": N, "window": seconds}}
                   If None, uses DEFAULT_LIMITS
        """
        self.limits = limits or self.DEFAULT_LIMITS.copy()
        
        # Track: {service: [(timestamp, count), ...]}
        self.buckets: Dict[str, list] = defaultdict(list)
        
        logger.info(f"Rate limiter initialized with {len(self.limits)} services")
    
    def is_allowed(self, service: str) -> bool:
        """Check if request is allowed for service.
        
        Args:
            service: Service name (e.g., "serper", "instagram")
            
        Returns:
            True if request allowed, False if rate limited
        """
        if service not in self.limits:
            logger.warning(f"Unknown service: {service}")
            return True  # Allow unknown services (fail open)
        
        limit_config = self.limits[service]
        limit = limit_config["limit"]
        window = limit_config["window"]
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)
        
        # Remove old entries outside the window
        self.buckets[service] = [ts for ts in self.buckets[service] if ts > cutoff]
        
        # Check if we've exceeded the limit
        if len(self.buckets[service]) >= limit:
            logger.warning(
                f"Rate limit exceeded for {service}: "
                f"{len(self.buckets[service])} requests in last {window}s (limit: {limit})"
            )
            return False
        
        # Record this request
        self.buckets[service].append(now)
        
        remaining = limit - len(self.buckets[service])
        logger.debug(f"Request allowed for {service} ({remaining} remaining)")
        
        return True
    
    def get_remaining(self, service: str) -> int:
        """Get remaining requests for service in current window.
        
        Args:
            service: Service name
            
        Returns:
            Number of remaining requests (0 if rate limited)
        """
        if service not in self.limits:
            return float('inf')
        
        limit_config = self.limits[service]
        limit = limit_config["limit"]
        window = limit_config["window"]
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)
        
        # Count valid requests in window
        valid_count = len([ts for ts in self.buckets[service] if ts > cutoff])
        
        return max(0, limit - valid_count)
    
    def reset(self, service: Optional[str] = None):
        """Reset rate limit counter.
        
        Args:
            service: Service to reset. If None, reset all services.
        """
        if service is None:
            self.buckets.clear()
            logger.info("Reset all rate limiter buckets")
        else:
            self.buckets[service] = []
            logger.info(f"Reset rate limiter for {service}")
    
    def get_stats(self) -> dict:
        """Get statistics on rate limit usage."""
        now = datetime.now()
        stats = {}
        
        for service, limit_config in self.limits.items():
            window = limit_config["window"]
            cutoff = now - timedelta(seconds=window)
            
            valid_count = len([ts for ts in self.buckets[service] if ts > cutoff])
            limit = limit_config["limit"]
            
            stats[service] = {
                "limit": limit,
                "window_seconds": window,
                "current_count": valid_count,
                "remaining": max(0, limit - valid_count),
                "percent_used": min(100, (valid_count / limit * 100) if limit > 0 else 0),
            }
        
        return stats


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
