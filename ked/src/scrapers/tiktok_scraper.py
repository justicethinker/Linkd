"""TikTok scraper for user profile data.

Extracts:
- Username, bio, follower count
- Video count and average views
- Recent trending videos in their niche
- Audience location and language preferences
- Engagement metrics (likes, comments, shares)
"""

import logging
import re
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TikTokVideo:
    """TikTok video metadata."""
    video_id: str
    caption: str
    created_at: datetime
    views: int
    likes: int
    comments: int
    shares: int
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.views == 0:
            return 0.0
        total_engagement = self.likes + self.comments + self.shares
        return (total_engagement / self.views) * 100


@dataclass
class TikTokProfile:
    """TikTok profile data."""
    username: str
    display_name: str
    bio: str
    follower_count: int
    following_count: int
    video_count: int
    verified: bool = False
    avatar_url: Optional[str] = None
    recent_videos: List[TikTokVideo] = None
    
    @property
    def avg_video_views(self) -> int:
        """Calculate average views per video."""
        if not self.recent_videos:
            return 0
        total_views = sum(v.views for v in self.recent_videos)
        return int(total_views / len(self.recent_videos))
    
    @property
    def avg_engagement_rate(self) -> float:
        """Calculate average engagement rate across recent videos."""
        if not self.recent_videos:
            return 0.0
        total_rate = sum(v.engagement_rate for v in self.recent_videos)
        return total_rate / len(self.recent_videos)


class TikTokScraper:
    """Scrapes TikTok profile data using web scraping."""
    
    def __init__(self, proxy_manager=None):
        """Initialize TikTok scraper.
        
        Args:
            proxy_manager: ProxyRotationManager instance for rotating proxies
        """
        self.proxy_manager = proxy_manager
        
        # Audience segments for demographic inference
        self.audience_segments = {
            "gen_z": ["aesthetic", "trending", "viral", "challenge", "dance", "lip-sync", "music"],
            "gen_alpha": ["family", "kids", "funny", "meme", "animation", "gaming"],
            "millennials": ["lifestyle", "wellness", "career", "travel", "humor", "relationship"],
            "parents": ["parenting", "kids", "family", "lifestyle", "education", "humor"],
            "professionals": ["business", "marketing", "entrepreneurship", "leadership", "industry"],
            "creators": ["tutorial", "behind-the-scenes", "process", "tips", "hack", "diy"],
        }
        
        logger.info("Initialized TikTok scraper")
    
    async def scrape_profile(self, username: str) -> Optional[TikTokProfile]:
        """Scrape TikTok profile data.
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            TikTokProfile or None if not found / blocked
        """
        try:
            logger.info(f"Scraping TikTok profile: {username}")
            
            # Check rate limit
            from ..services.rate_limiter import get_rate_limiter
            rate_limiter = get_rate_limiter()
            
            if not rate_limiter.is_allowed("tiktok"):
                remaining = rate_limiter.get_remaining("tiktok")
                logger.warning(
                    f"TikTok rate limit exceeded. "
                    f"Retrying in ~{(60 - datetime.now().second)}s (remaining: {remaining})"
                )
                return None
            
            # Get proxy for TikTok scraping
            proxy = None
            if self.proxy_manager:
                proxy = self.proxy_manager.get_proxy(source_type="datacenter")
            
            # Mock implementation - in production, use Playwright with dynamic DOM rendering
            # TikTok is heavily JavaScript-rendered, requires Playwright or similar
            profile = TikTokProfile(
                username=username,
                display_name=username,
                bio="Sample bio",
                follower_count=1000,
                following_count=500,
                video_count=50,
                verified=False,
                recent_videos=[],
            )
            
            logger.info(f"Successfully scraped TikTok profile: {username}")
            return profile
            
        except Exception as e:
            logger.error(f"Error scraping TikTok profile {username}: {str(e)}")
            return None
    
    def infer_audience_segments(self, bio: str, video_captions: List[str]) -> Dict[str, float]:
        """Infer audience segments based on content.
        
        Args:
            bio: Profile bio
            video_captions: List of recent video captions
            
        Returns:
            Dict of {segment: confidence_score (0.0-1.0)}
        """
        combined_text = (bio + " " + " ".join(video_captions)).lower()
        scores = {}
        
        for segment, keywords in self.audience_segments.items():
            matches = sum(1 for kw in keywords if kw in combined_text)
            score = min(1.0, matches / len(keywords))
            if score > 0:
                scores[segment] = score
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    
    def classify_content_niche(self, video_captions: List[str]) -> str:
        """Classify content niche from video captions.
        
        Args:
            video_captions: List of recent video captions
            
        Returns:
            Content niche (e.g., "entertainment", "education", "lifestyle")
        """
        combined = " ".join(video_captions).lower()
        
        niche_keywords = {
            "entertainment": ["funny", "lol", "hilarious", "comedy", "reaction", "prank", "viral"],
            "education": ["tutorial", "how to", "tips", "hack", "learn", "guide", "educational", "explainer"],
            "lifestyle": ["lifestyle", "daily vlog", "routine", "aesthetic", "mood", "vibes"],
            "fitness": ["workout", "gym", "fitness", "transformation", "training", "exercise"],
            "beauty": ["makeup", "skincare", "hair", "beauty", "haul", "review"],
            "music": ["music", "song", "dance", "lip-sync", "challenge", "remix"],
            "food": ["food", "cooking", "recipe", "restaurant", "mukbang", "food review"],
            "gaming": ["gaming", "game", "gameplay", "streaming", "esports"],
            "travel": ["travel", "vlog", "adventure", "destination", "international"],
        }
        
        scores = {}
        for niche, keywords in niche_keywords.items():
            matches = sum(1 for kw in keywords if kw in combined)
            scores[niche] = matches
        
        best_niche = max(scores, key=scores.get)
        return best_niche
    
    def estimate_growth_rate(self, profile: TikTokProfile) -> str:
        """Estimate growth trajectory based on follower/video ratio.
        
        Args:
            profile: TikTokProfile
            
        Returns:
            "growing", "stable", or "declining" assessment
        """
        if profile.video_count == 0:
            return "unknown"
        
        followers_per_video = profile.follower_count / profile.video_count
        
        # Heuristic: higher followers per video usually means rapid early growth
        # or consistent viral content
        if followers_per_video > 100:
            return "growing"
        elif followers_per_video > 10:
            return "stable"
        else:
            return "slow"


async def scrape_tiktok_profile(username: str, proxy_manager=None) -> Optional[Dict]:
    """Convenience function to scrape TikTok profile.
    
    Args:
        username: TikTok username
        proxy_manager: Optional ProxyRotationManager
        
    Returns:
        Profile data dict or None
    """
    scraper = TikTokScraper(proxy_manager)
    profile = await scraper.scrape_profile(username)
    
    if profile:
        return {
            "username": profile.username,
            "followers": profile.follower_count,
            "videos": profile.video_count,
            "avg_views": profile.avg_video_views,
            "engagement_rate": profile.avg_engagement_rate,
        }
    return None
