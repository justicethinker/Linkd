"""Proxy rotation manager for distributed scraping.

Prevents IP blacklisting by rotating through a proxy pool.
Supports multiple proxy services (BrightData, Oxylabs, etc.).
"""

import logging
import random
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    url: str
    source: str  # "brightdata", "oxylabs", "residential", "datacenter"
    last_used: datetime = None
    failure_count: int = 0
    success_count: int = 0
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability score based on success/failure ratio."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total


class ProxyRotationManager:
    """Manages proxy rotation for web scraping operations."""
    
    def __init__(self, proxy_configs: List[ProxyConfig] = None):
        """Initialize with proxy pool.
        
        Args:
            proxy_configs: List of proxy configurations.
                          If None, uses environment variables or free tier.
        """
        self.proxy_configs = proxy_configs or self._load_from_env()
        self.current_index = 0
        logger.info(f"Initialized proxy manager with {len(self.proxy_configs)} proxies")
    
    def _load_from_env(self) -> List[ProxyConfig]:
        """Load proxies from environment variables.
        
        Expected format:
        PROXY_URLS=http://proxy1:port,http://proxy2:port,...
        PROXY_SOURCES=brightdata,oxylabs,...
        """
        from ..config import settings
        
        proxy_urls = getattr(settings, 'proxy_urls', '')
        proxy_sources = getattr(settings, 'proxy_sources', '')
        
        if not proxy_urls:
            logger.warning("No proxy URLs configured. Using direct connections (higher risk of blocking).")
            return []
        
        urls = proxy_urls.split(',')
        sources = proxy_sources.split(',') if proxy_sources else ['datacenter'] * len(urls)
        
        configs = [
            ProxyConfig(url=url.strip(), source=source.strip())
            for url, source in zip(urls, sources)
        ]
        
        return configs
    
    def get_proxy(self, source_type: str = "datacenter") -> Optional[dict]:
        """Get next proxy, preferring the requested source type.
        
        Uses weighted random selection based on reliability scores.
        Avoids recently-failed proxies.
        
        Args:
            source_type: Preferred proxy source type
            
        Returns:
            Dict with 'http' and 'https' proxy URLs, or None if no proxies available
        """
        if not self.proxy_configs:
            logger.debug("No proxies configured")
            return None
        
        # Filter proxies by source type preference
        matching = [p for p in self.proxy_configs if p.source == source_type]
        if not matching:
            matching = self.proxy_configs  # Fall back to any proxy
        
        # Weight by reliability score (avoid broken proxies)
        scores = [p.reliability_score for p in matching]
        total_score = sum(scores)
        
        if total_score == 0:
            selected = random.choice(matching)
        else:
            # Weighted random selection
            weights = [s / total_score for s in scores]
            selected = random.choices(matching, weights=weights, k=1)[0]
        
        # Mark as recently used
        selected.last_used = datetime.now()
        
        proxy_url = selected.url
        logger.debug(f"Selected proxy: {proxy_url} (reliability: {selected.reliability_score:.2%})")
        
        return {
            "http": proxy_url,
            "https": proxy_url,
        }
    
    def record_success(self, proxy_url: str):
        """Record successful use of proxy.
        
        Args:
            proxy_url: Proxy URL that succeeded
        """
        for config in self.proxy_configs:
            if config.url == proxy_url:
                config.success_count += 1
                logger.debug(f"Proxy success recorded: {proxy_url} (score: {config.reliability_score:.2%})")
                break
    
    def record_failure(self, proxy_url: str):
        """Record failed use of proxy.
        
        Args:
            proxy_url: Proxy URL that failed
        """
        for config in self.proxy_configs:
            if config.url == proxy_url:
                config.failure_count += 1
                logger.warning(f"Proxy failure recorded: {proxy_url} (score: {config.reliability_score:.2%})")
                break
    
    def get_stats(self) -> dict:
        """Get statistics on proxy performance."""
        return {
            "total_proxies": len(self.proxy_configs),
            "proxies": [
                {
                    "url": p.url,
                    "source": p.source,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count,
                    "reliability_score": p.reliability_score,
                    "last_used": p.last_used.isoformat() if p.last_used else None,
                }
                for p in self.proxy_configs
            ]
        }


# Global proxy manager instance
_proxy_manager = None


def get_proxy_manager() -> ProxyRotationManager:
    """Get or create global proxy manager."""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyRotationManager()
    return _proxy_manager
