"""Social Quadrant mapping for personality profiling.

Maps a person across 4 dimensions:
1. Professional Axis (LinkedIn, GitHub, work-focused content)
2. Creative Axis (Instagram, TikTok, personal branding)
3. Casual Axis (Twitter, memes, off-topic discussion)
4. Real-time Axis (recency of activity, trending topics)

Used to predict communication style and outreach strategy.
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SocialQuadrant:
    """Person's placement in 4D social space."""
    professional: float  # 0.0-1.0: LinkedIn activity, GitHub presence, career focus
    creative: float      # 0.0-1.0: Instagram, TikTok, personal brand, content creation
    casual: float        # 0.0-1.0: Twitter frequency, casual topics, meme sharing
    realtime: float      # 0.0-1.0: Recent activity freshness, trending topics
    
    @property
    def profile_type(self) -> str:
        """Classify profile type based on quadrant position."""
        # Find dominant axes
        dims = {
            'professional': self.professional,
            'creative': self.creative,
            'casual': self.casual,
            'realtime': self.realtime,
        }
        
        top_two = sorted(dims.items(), key=lambda x: x[1], reverse=True)[:2]
        primary = top_two[0][0]
        secondary = top_two[1][0]
        
        return f"{primary}_{secondary}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "professional": round(self.professional, 3),
            "creative": round(self.creative, 3),
            "casual": round(self.casual, 3),
            "realtime": round(self.realtime, 3),
            "profile_type": self.profile_type,
        }


class SocialQuadrantMapper:
    """Maps person across 4D social space."""
    
    def __init__(self):
        """Initialize quadrant mapper."""
        logger.info("Initialized SocialQuadrantMapper")
    
    def calculate_from_sources(self, sources_data: Dict) -> SocialQuadrant:
        """Calculate quadrant from scraped social media data.
        
        Args:
            sources_data: Dict with platform data
                {
                    "linkedin": {
                        "headline": "...",
                        "experience": [...],
                        "skills": [...]
                    },
                    "github": {
                        "languages": [...],
                        "stars": ...,
                        "repos": [...]
                    },
                    "instagram": {
                        "follower_count": ...,
                        "bio": "...",
                        "post_count": 42,
                        "recent_posts": [...]
                    },
                    "twitter": {
                        "follower_count": ...,
                        "tweet_count": ...,
                        "recent_tweets": [...]
                    },
                    "tiktok": {
                        "bio": "...",
                        "follower_count": ...,
                        "video_count": ...,
                        "recent_videos": [...]
                    }
                }
            
        Returns:
            SocialQuadrant with calculated scores
        """
        
        # Calculate Professional Axis: LinkedIn + GitHub + work focus
        professional = self._calculate_professional(sources_data)
        
        # Calculate Creative Axis: Instagram + TikTok + personal branding
        creative = self._calculate_creative(sources_data)
        
        # Calculate Casual Axis: Twitter frequency + casual topics
        casual = self._calculate_casual(sources_data)
        
        # Calculate Real-time Axis: Activity recency
        realtime = self._calculate_realtime(sources_data)
        
        # Normalize to (0.0-1.0) range
        max_val = max(professional, creative, casual, realtime, 0.1)  # Avoid division by zero
        
        quadrant = SocialQuadrant(
            professional=min(1.0, professional / max_val),
            creative=min(1.0, creative / max_val),
            casual=min(1.0, casual / max_val),
            realtime=min(1.0, realtime / max_val),
        )
        
        logger.info(f"Calculated quadrant: {quadrant.to_dict()}")
        return quadrant
    
    def _calculate_professional(self, sources_data: Dict) -> float:
        """Calculate professional axis score.
        
        Based on:
        - LinkedIn presence and engagement
        - GitHub presence and contribution
        - Work-focused content
        """
        score = 0.0
        
        # LinkedIn signals
        linkedin = sources_data.get("linkedin", {})
        if linkedin:
            if linkedin.get("headline"):
                score += 0.2  # Has professional headline
            if linkedin.get("experience"):
                score += 0.3  # Has work history
            if linkedin.get("skills"):
                score += 0.2  # Has skills (shows active profile)
        
        # GitHub signals
        github = sources_data.get("github", {})
        if github:
            stars = github.get("stars", 0)
            if stars > 0:
                score += min(0.3, 0.3 * (stars / 100))  # Normalize: 100 stars = max
            if github.get("repos"):
                score += 0.1
        
        return score
    
    def _calculate_creative(self, sources_data: Dict) -> float:
        """Calculate creative axis score.
        
        Based on:
        - Instagram presence and content
        - TikTok presence and engagement
        - Personal branding signals
        """
        score = 0.0
        
        # Instagram signals
        instagram = sources_data.get("instagram", {})
        if instagram:
            if instagram.get("bio"):
                score += 0.15
            posts = instagram.get("post_count", 0)
            if posts > 0:
                score += min(0.25, 0.25 * (posts / 100))  # Normalize: 100 posts = max
            if instagram.get("follower_count", 0) > 100:
                score += 0.2
        
        # TikTok signals
        tiktok = sources_data.get("tiktok", {})
        if tiktok:
            if tiktok.get("bio"):
                score += 0.15
            videos = tiktok.get("video_count", 0)
            if videos > 0:
                score += min(0.25, 0.25 * (videos / 100))  # Normalize: 100 videos = max
        
        return score
    
    def _calculate_casual(self, sources_data: Dict) -> float:
        """Calculate casual axis score.
        
        Based on:
        - Twitter/X presence and frequency
        - Casual topic discussion
        - Social engagement
        """
        score = 0.0
        
        twitter = sources_data.get("twitter", {})
        if twitter:
            if twitter.get("follower_count", 0) > 100:
                score += 0.3
            tweets = twitter.get("tweet_count", 0)
            if tweets > 0:
                score += min(0.4, 0.4 * (tweets / 1000))  # Normalize: 1000 tweets = max
            
            # Check for casual content in recent tweets
            recent_tweets = twitter.get("recent_tweets", [])
            casual_keywords = ["lol", "haha", "meme", "funny", "just", "honestly", "tbh"]
            casual_count = sum(
                1 for tweet in recent_tweets
                if any(kw in tweet.get("text", "").lower() for kw in casual_keywords)
            )
            score += min(0.3, 0.3 * (casual_count / len(recent_tweets)) if recent_tweets else 0)
        
        return score
    
    def _calculate_realtime(self, sources_data: Dict) -> float:
        """Calculate real-time axis score.
        
        Based on:
        - Recency of activity
        - Trending topic engagement
        - Frequency of updates
        """
        score = 0.0
        now = datetime.now()
        
        # Check for recent activity across all sources
        last_activities = []
        
        # Twitter activity
        twitter = sources_data.get("twitter", {})
        if twitter and twitter.get("recent_tweets"):
            last_activities.append(twitter["recent_tweets"][0].get("created_at", now))
        
        # Instagram activity
        instagram = sources_data.get("instagram", {})
        if instagram and instagram.get("recent_posts"):
            last_activities.append(instagram["recent_posts"][0].get("created_at", now))
        
        # TikTok activity
        tiktok = sources_data.get("tiktok", {})
        if tiktok and tiktok.get("recent_videos"):
            last_activities.append(tiktok["recent_videos"][0].get("created_at", now))
        
        if last_activities:
            # Calculate avg time since last activity
            avg_time_since = sum(
                (now - (act if isinstance(act, datetime) else datetime.fromisoformat(str(act)))).total_seconds()
                for act in last_activities
            ) / len(last_activities)
            
            # Score: Recent = high, old = low
            # 1 day = 0.8, 1 week = 0.4, 1 month = 0.1
            days_old = avg_time_since / (24 * 3600)
            
            if days_old <= 1:
                score = 1.0
            elif days_old <= 7:
                score = 0.8 - (days_old - 1) * 0.057  # Linear decay from 0.8 to 0.3 over 12 days
            elif days_old <= 30:
                score = max(0.1, 0.3 - (days_old - 7) * 0.01)
            else:
                score = 0.0
        
        return min(1.0, score)
    
    def get_communication_strategy(self, quadrant: SocialQuadrant) -> dict:
        """Get recommended communication strategy based on quadrant.
        
        Args:
            quadrant: SocialQuadrant with calculated scores
            
        Returns:
            Dict with communication recommendations
        """
        strategy = {
            "profile_type": quadrant.profile_type,
            "recommended_channels": [],
            "messaging_tone": "",
            "content_focus": "",
        }
        
        # Recommend channels based on highest scores
        channels = [
            ("professional", quadrant.professional, ["LinkedIn", "Email", "GitHub"]),
            ("creative", quadrant.creative, ["Instagram", "TikTok", "Portfolio"]),
            ("casual", quadrant.casual, ["Twitter", "Discord", "Slack"]),
            ("realtime", quadrant.realtime, ["Twitter", "LinkedIn Feed", "Email"]),
        ]
        
        # Sort by score and recommend top channels
        channels.sort(key=lambda x: x[1], reverse=True)
        seen_channels = set()
        for _, _, channel_list in channels[:2]:  # Use top 2 dimensions
            for ch in channel_list:
                if ch not in seen_channels:
                    strategy["recommended_channels"].append(ch)
                    seen_channels.add(ch)
        
        # Tone recommendations
        if quadrant.professional > 0.7:
            strategy["messaging_tone"] = "formal, industry-focused"
        elif quadrant.creative > 0.7:
            strategy["messaging_tone"] = "personable, creative, visual"
        elif quadrant.casual > 0.7:
            strategy["messaging_tone"] = "conversational, friendly"
        else:
            strategy["messaging_tone"] = "balanced, professional but warm"
        
        # Content focus
        if quadrant.professional > 0.7:
            strategy["content_focus"] = "Career opportunities, industry trends"
        elif quadrant.creative > 0.7:
            strategy["content_focus"] = "Creative projects, aesthetic appeal"
        elif quadrant.casual > 0.7:
            strategy["content_focus"] = "Community, shared interests, fun facts"
        else:
            strategy["content_focus"] = "Versatile - highlight relevant aspects"
        
        return strategy


# Global mapper instance
_mapper = None


def get_social_quadrant_mapper() -> SocialQuadrantMapper:
    """Get or create global mapper."""
    global _mapper
    if _mapper is None:
        _mapper = SocialQuadrantMapper()
    return _mapper
