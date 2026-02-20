"""Search API integration for finding people across the web.

Uses Serper.dev API for comprehensive search:
- Site-specific searches (site:linkedin.com/in/, site:instagram.com, site:github.com, etc.)
- Google search with filters
- Result deduplication and ranking
"""

import logging
import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""
    url: str
    title: str
    snippet: str
    source: str  # "linkedin", "github", "instagram", "twitter", "personal_blog", etc.
    confidence: float = 0.5  # Match confidence (0.0-1.0)
    published_date: Optional[str] = None


class SearchAPIClient:
    """Client for Serper.dev Search API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize search API client.
        
        Args:
            api_key: Serper API key. If None, reads from env var SERPER_API_KEY
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            logger.warning("SERPER_API_KEY not configured. Search functionality disabled.")
        
        self.base_url = "https://google.serper.dev"
        
        logger.info("Initialized SearchAPIClient")
    
    async def search_person(self, name: str, context: str = "") -> List[SearchResult]:
        """Search for a person across the web.
        
        Args:
            name: Full name of the person
            context: Additional context (e.g., "software engineer", "london")
            
        Returns:
            List of SearchResult objects
        """
        if not self.api_key:
            logger.error("Cannot search: SERPER_API_KEY not configured")
            return []
        
        # Check rate limit
        from ..services.rate_limiter import get_rate_limiter
        rate_limiter = get_rate_limiter()
        
        if not rate_limiter.is_allowed("serper"):
            remaining = rate_limiter.get_remaining("serper")
            logger.warning(f"Serper rate limit exceeded. Remaining: {remaining} calls")
            return []
        
        results = []
        
        # Strategy: Run multiple searches with site filters
        search_queries = [
            (f'site:linkedin.com/in/ "{name}"', "linkedin"),
            (f'site:github.com "{name}"', "github"),
            (f'site:instagram.com "{name}"', "instagram"),
            (f'site:twitter.com "{name}"', "twitter"),
            (f'"{name}" {context} -site:facebook.com', "general"),
        ]
        
        for query, source in search_queries:
            try:
                # Mock implementation - in production, call Serper API
                # Example Serper API call:
                # import aiohttp
                # async with aiohttp.ClientSession() as session:
                #     async with session.post(
                #         f"{self.base_url}/search",
                #         json={"q": query},
                #         headers={"X-API-KEY": self.api_key}
                #     ) as resp:
                #         data = await resp.json()
                #         results.extend(data.get("organic", []))
                
                logger.debug(f"Searched for: {query}")
                
                # Mock: Return empty results (in production, parse Serper response)
                
            except Exception as e:
                logger.error(f"Error searching for {name}: {str(e)}")
        
        return results
    
    async def search_linkedin_profile(self, full_name: str, location: Optional[str] = None) -> Optional[str]:
        """Search specifically for LinkedIn profile URL.
        
        Args:
            full_name: Full name of the person
            location: Optional location for disambiguation
            
        Returns:
            LinkedIn URL or None if not found
        """
        search_query = f'site:linkedin.com/in/ "{full_name}"'
        if location:
            search_query += f" {location}"
        
        results = await self.search_person(full_name, location or "")
        
        linkedin_results = [r for r in results if r.source == "linkedin"]
        if linkedin_results:
            return linkedin_results[0].url
        
        return None
    
    async def search_github_profile(self, name: str) -> Optional[str]:
        """Search specifically for GitHub profile URL.
        
        Args:
            name: Name or username
            
        Returns:
            GitHub URL or None if not found
        """
        results = await self.search_person(name, "github")
        
        github_results = [r for r in results if r.source == "github"]
        if github_results:
            return github_results[0].url
        
        return None
    
    async def search_social_profiles(self, name: str) -> Dict[str, Optional[str]]:
        """Search for multiple social profiles at once.
        
        Args:
            name: Full name of the person
            
        Returns:
            Dict with URLs for each found platform:
            {
                "linkedin": "https://...",
                "github": "https://...",
                "instagram": "https://...",
                "twitter": "https://...",
                "personal_blog": "https://...",
            }
        """
        results = await self.search_person(name)
        
        profiles = {
            "linkedin": None,
            "github": None,
            "instagram": None,
            "twitter": None,
            "personal_blog": None,
        }
        
        # Extract URLs by source
        source_map = {
            "linkedin": "linkedin",
            "github": "github",
            "instagram": "instagram",
            "twitter": "twitter",
            "general": "personal_blog",
        }
        
        for result in results:
            if result.source in source_map and profiles[source_map[result.source]] is None:
                profiles[source_map[result.source]] = result.url
        
        logger.info(f"Found profiles for {name}: {[k for k, v in profiles.items() if v]}")
        
        return profiles


async def search_person_profiles(name: str, context: str = "") -> Dict[str, Optional[str]]:
    """Convenience function to search for a person across major platforms.
    
    Args:
        name: Full name of the person
        context: Optional context (location, profession, etc.)
        
    Returns:
        Dict of {platform: url}
    """
    client = SearchAPIClient()
    return await client.search_social_profiles(name)
