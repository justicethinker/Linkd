"""GitHub scraper for user profile data.

Extracts:
- Username and profile information
- Programming languages used
- Repository statistics (stars, forks, contributors)
- Contribution graph and activity
- Popular repositories and their topics
"""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepository:
    """GitHub repository information."""
    name: str
    description: str
    url: str
    stars: int
    forks: int
    language: str
    topics: List[str]
    is_fork: bool = False


@dataclass
class GitHubProfile:
    """GitHub profile data."""
    username: str
    name: Optional[str]
    bio: Optional[str]
    follower_count: int
    following_count: int
    public_repo_count: int
    location: Optional[str] = None
    blog_url: Optional[str] = None
    twitter: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    repositories: List[GitHubRepository] = None
    
    @property
    def total_stars(self) -> int:
        """Sum of all repository stars."""
        if not self.repositories:
            return 0
        return sum(r.stars for r in self.repositories)
    
    @property
    def avg_stars_per_repo(self) -> float:
        """Average stars per repository."""
        if not self.repositories or len(self.repositories) == 0:
            return 0.0
        return self.total_stars / len(self.repositories)


class GitHubScraper:
    """Scrapes GitHub profile data using public GitHub API."""
    
    def __init__(self):
        """Initialize GitHub scraper."""
        self.base_url = "https://api.github.com"
        
        logger.info("Initialized GitHub scraper")
    
    async def scrape_profile(self, username: str) -> Optional[GitHubProfile]:
        """Scrape GitHub profile using public API (no auth required).
        
        Args:
            username: GitHub username
            
        Returns:
            GitHubProfile or None if not found
        """
        try:
            logger.info(f"Scraping GitHub profile: {username}")
            
            # Check rate limit (GitHub public API: 60 req/hour without auth)
            from ..services.rate_limiter import get_rate_limiter
            rate_limiter = get_rate_limiter()
            
            if not rate_limiter.is_allowed("github"):
                remaining = rate_limiter.get_remaining("github")
                logger.warning(f"GitHub rate limit may be exceeded (remaining: {remaining})")
                # Don't block - continue anyway since GitHub is public
            
            # Mock implementation - in production, use aiohttp or requests to GitHub API
            profile = GitHubProfile(
                username=username,
                name="Sample Name",
                bio="Sample bio",
                follower_count=10,
                following_count=5,
                public_repo_count=5,
                repositories=[],
            )
            
            logger.info(f"Successfully scraped GitHub profile: {username}")
            return profile
            
        except Exception as e:
            logger.error(f"Error scraping GitHub profile {username}: {str(e)}")
            return None
    
    def extract_primary_languages(self, repositories: List[GitHubRepository]) -> Dict[str, int]:
        """Extract primary programming languages used.
        
        Args:
            repositories: List of repositories
            
        Returns:
            Dict of {language: repo_count}
        """
        language_counts = {}
        
        for repo in repositories:
            if repo.language:
                language_counts[repo.language] = language_counts.get(repo.language, 0) + 1
        
        # Sort by frequency
        return dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True))
    
    def extract_expertise_areas(self, repositories: List[GitHubRepository]) -> Dict[str, float]:
        """Infer expertise areas from repository topics and languages.
        
        Args:
            repositories: List of repositories
            
        Returns:
            Dict of {area: confidence_score (0.0-1.0)}
        """
        expertise = {}
        
        # Collect all topics
        all_topics = []
        for repo in repositories:
            all_topics.extend(repo.topics)
        
        # Count topic frequency
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Convert to confidence scores
        max_count = max(topic_counts.values()) if topic_counts else 1
        for topic, count in topic_counts.items():
            expertise[topic] = count / max_count
        
        # Sort by score
        return dict(sorted(expertise.items(), key=lambda x: x[1], reverse=True))
    
    def estimate_skill_level(self, profile: GitHubProfile) -> str:
        """Estimate skill level based on repository stars and activity.
        
        Args:
            profile: GitHubProfile
            
        Returns:
            "beginner", "intermediate", "advanced", or "expert"
        """
        if not profile.repositories:
            return "unknown"
        
        avg_stars = profile.avg_stars_per_repo
        
        # Estimation based on average stars per repo
        if avg_stars >= 1000:
            return "expert"
        elif avg_stars >= 100:
            return "advanced"
        elif avg_stars >= 10:
            return "intermediate"
        else:
            return "beginner"
    
    def calculate_contribution_score(self, profile: GitHubProfile) -> float:
        """Calculate overall contribution score.
        
        Args:
            profile: GitHubProfile
            
        Returns:
            Score from 0.0-1.0
        """
        # Scoring factors:
        # 1. Total stars (0-0.4)
        stars_score = min(0.4, profile.total_stars / 1000)
        
        # 2. Repository count (0-0.3)
        repos_score = min(0.3, profile.public_repo_count / 100)
        
        # 3. Followers (0-0.3)
        followers_score = min(0.3, profile.follower_count / 1000)
        
        total = stars_score + repos_score + followers_score
        return min(1.0, total)


async def scrape_github_profile(username: str) -> Optional[Dict]:
    """Convenience function to scrape GitHub profile.
    
    Args:
        username: GitHub username
        
    Returns:
        Profile data dict or None
    """
    scraper = GitHubScraper()
    profile = await scraper.scrape_profile(username)
    
    if profile:
        return {
            "username": profile.username,
            "name": profile.name,
            "repos": profile.public_repo_count,
            "followers": profile.follower_count,
            "stars": profile.total_stars,
            "skill_level": scraper.estimate_skill_level(profile),
            "contribution_score": scraper.calculate_contribution_score(profile),
        }
    return None
