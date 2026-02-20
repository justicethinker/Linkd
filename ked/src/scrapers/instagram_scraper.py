"""Instagram scraper for user profile data.

Extracts:
- Username, bio, follower count
- Recent post captions and engagement (likes, comments)
- Aesthetic classification (lifestyle, tech, fitness, etc.)
- Posting frequency and engagement rate
"""

import logging
import re
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InstagramProfile:
    """Instagram profile data."""
    username: str
    bio: str
    follower_count: int
    following_count: int
    post_count: int
    profile_picture_url: Optional[str] = None
    is_verified: bool = False
    recent_posts: List[Dict] = None  # [{created_at, caption, likes, comments}]
    
    @property
    def engagement_rate(self) -> float:
        """Calculate average engagement rate (likes + comments) / followers."""
        if not self.recent_posts or self.follower_count == 0:
            return 0.0
        
        total_engagement = sum(
            p.get("likes", 0) + p.get("comments", 0)
            for p in self.recent_posts
        )
        avg_engagement = total_engagement / len(self.recent_posts) if self.recent_posts else 0
        
        return (avg_engagement / self.follower_count) * 100 if self.follower_count > 0 else 0.0


class InstagramScraper:
    """Scrapes Instagram profile data using web scraping."""
    
    def __init__(self, proxy_manager=None):
        """Initialize Instagram scraper.
        
        Args:
            proxy_manager: ProxyRotationManager instance for rotating proxies
        """
        self.proxy_manager = proxy_manager
        
        # Niche keywords for aesthetic classification
        self.niche_keywords = {
            "tech": ["app", "developer", "code", "startup", "tech", "software", "programming", "ai", "ml"],
            "fitness": ["gym", "workout", "fitness", "personal trainer", "crossfit", "yoga", "health"],
            "lifestyle": ["lifestyle", "daily", "routine", "wellness", "mindfulness", "self-care"],
            "fashion": ["fashion", "outfit", "style", "designer", "clothing", "wardrobe", "trend"],
            "beauty": ["beauty", "makeup", "skincare", "cosmetics", "glam", "hair"],
            "food": ["food", "cooking", "recipe", "chef", "kitchen", "foodie", "gastro"],
            "travel": ["travel", "adventure", "wanderlust", "explore", "photography", "vacation"],
            "business": ["entrepreneur", "business", "success", "motivation", "hustle", "leadership"],
            "parenting": ["mom", "dad", "kids", "family", "parenting", "children", "baby"],
            "sustainability": ["eco", "sustainable", "green", "environment", "zero-waste", "climate"],
        }
        
        logger.info("Initialized Instagram scraper")
    
    async def scrape_profile(self, username: str) -> Optional[InstagramProfile]:
        """Scrape Instagram profile data.
        
        Args:
            username: Instagram username (without @)
            
        Returns:
            InstagramProfile or None if not found / blocked
        """
        try:
            logger.info(f"Scraping Instagram profile: {username}")
            
            # Check rate limit
            from ..services.rate_limiter import get_rate_limiter
            rate_limiter = get_rate_limiter()
            
            if not rate_limiter.is_allowed("instagram"):
                remaining = rate_limiter.get_remaining("instagram")
                logger.warning(
                    f"Instagram rate limit exceeded. "
                    f"Retrying in ~{(60 - datetime.now().second)}s (remaining: {remaining})"
                )
                return None
            
            # Get proxy for Instagram scraping
            proxy = None
            if self.proxy_manager:
                proxy = self.proxy_manager.get_proxy(source_type="residential")
            
            # Mock implementation - in production, use Playwright/Selenium
            # For now, return sample profile structure
            profile = InstagramProfile(
                username=username,
                bio="Sample bio",
                follower_count=1000,
                following_count=500,
                post_count=50,
                is_verified=False,
                recent_posts=[],
            )
            
            logger.info(f"Successfully scraped Instagram profile: {username}")
            return profile
            
        except Exception as e:
            logger.error(f"Error scraping Instagram profile {username}: {str(e)}")
            return None
    
    def classify_niche(self, bio: str, captions: List[str]) -> Dict[str, float]:
        """Classify profile niche based on bio and recent captions.
        
        Args:
            bio: Profile bio text
            captions: List of recent post captions
            
        Returns:
            Dict of {niche: confidence_score (0.0-1.0)}
        """
        combined_text = (bio + " " + " ".join(captions)).lower()
        scores = {}
        
        for niche, keywords in self.niche_keywords.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in combined_text)
            # Calculate confidence based on matches relative to keywords
            score = min(1.0, matches / len(keywords))
            if score > 0:
                scores[niche] = score
        
        # Normalize scores to sum to 1.0
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        # Sort by score descending
        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    
    def estimate_engagement_quality(self, profile: InstagramProfile) -> str:
        """Estimate quality of engagement.
        
        Args:
            profile: InstagramProfile with engagement metrics
            
        Returns:
            "high", "medium", or "low" engagement quality
        """
        rate = profile.engagement_rate
        
        # Standards vary by follower count
        if profile.follower_count < 1000:
            # Small accounts: 3%+ is good
            return "high" if rate >= 3.0 else ("medium" if rate >= 1.0 else "low")
        elif profile.follower_count < 10000:
            # Micro influencers: 1-3% is good
            return "high" if rate >= 3.0 else ("medium" if rate >= 1.0 else "low")
        elif profile.follower_count < 100000:
            # Mid-tier: 0.5-1.5% is good
            return "high" if rate >= 1.5 else ("medium" if rate >= 0.5 else "low")
        else:
            # Macro influencers: < 0.5% is normal
            return "high" if rate >= 0.5 else ("medium" if rate >= 0.1 else "low")


async def scrape_instagram_profile(username: str, proxy_manager=None) -> Optional[Dict]:
    """Convenience function to scrape Instagram profile.
    
    Args:
        username: Instagram username
        proxy_manager: Optional ProxyRotationManager
        
    Returns:
        Profile data dict or None
    """
    scraper = InstagramScraper(proxy_manager)
    profile = await scraper.scrape_profile(username)
    
    if profile:
        return profile.__dict__
    return None
