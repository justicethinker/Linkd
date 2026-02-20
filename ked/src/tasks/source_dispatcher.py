"""Source dispatcher task for Phase 2b multi-source enrichment.

Coordinates parallel queries to 6-8 data sources:
1. LinkedIn (professional profiles)
2. Instagram (creative/personal brand)
3. TikTok (content creator presence)
4. GitHub (technical profile)
5. Twitter/X (real-time presence)
6. General web search (blogs, articles, mentions)
7. YouTube (video content and channels)
8. Bluesky (emerging platform)

Returns aggregated results for identity resolution and synthesis.
"""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SourceDispatcher:
    """Orchestrates parallel source queries."""
    
    def __init__(self):
        """Initialize source dispatcher."""
        self.sources = {
            "linkedin": self._query_linkedin,
            "instagram": self._query_instagram,
            "tiktok": self._query_tiktok,
            "github": self._query_github,
            "twitter": self._query_twitter,
            "search": self._query_search,
            "youtube": self._query_youtube,
            "bluesky": self._query_bluesky,
        }
        
        logger.info("Initialized SourceDispatcher")
    
    async def dispatch_to_sources(
        self,
        person_name: str,
        context: Optional[str] = None,
        enabled_sources: Optional[List[str]] = None,
    ) -> Dict:
        """Fan out to all enabled sources in parallel.
        
        Args:
            person_name: Name to search for
            context: Additional context (location, profession, etc.)
            enabled_sources: Optional list of sources to query (defaults to all)
                           If any source fails, gracefully skips it.
            
        Returns:
            Dict with results from all sources:
            {
                "sources_queried": ["linkedin", "github", ...],
                "sources_found": [
                    {
                        "source": "linkedin",
                        "profiles": [
                            {
                                "name": "...",
                                "url": "...",
                                "profile_data": {...}
                            }
                        ],
                        "query_time_ms": 1234,
                        "success": true
                    },
                    ...
                ],
                "sources_failed": ["twitter", ...],
                "total_candidates": 12,
                "dispatch_time_ms": 5678
            }
        """
        start_time = datetime.now()
        
        # Determine which sources to query
        if enabled_sources is None:
            enabled_sources = list(self.sources.keys())
        else:
            # Filter to only known sources
            enabled_sources = [s for s in enabled_sources if s in self.sources]
        
        logger.info(f"Dispatching to {len(enabled_sources)} sources")
        
        # Create tasks for all sources
        tasks = {
            source: self.sources[source](person_name, context)
            for source in enabled_sources
        }
        
        # Wait for all tasks concurrently (gather with return_exceptions)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Process results
        sources_found = []
        sources_failed = []
        total_candidates = 0
        
        for source, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                # Source query failed
                logger.warning(f"Source {source} failed: {str(result)}")
                sources_failed.append(source)
            elif result is None:
                # Source returned no results (but didn't error)
                logger.debug(f"Source {source} returned no results")
                sources_failed.append(source)
            else:
                # Source returned results
                sources_found.append(result)
                total_candidates += len(result.get("profiles", []))
        
        elapsed = datetime.now() - start_time
        
        return {
            "sources_queried": enabled_sources,
            "sources_found": sources_found,
            "sources_failed": sources_failed,
            "total_candidates": total_candidates,
            "dispatch_time_ms": int(elapsed.total_seconds() * 1000),
        }
    
    async def _query_linkedin(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query LinkedIn for profiles.
        
        Args:
            name: Person name
            context: Optional context
            
        Returns:
            Dict with LinkedIn results or None
        """
        try:
            start = datetime.now()
            
            # Try search API first
            from ..scrapers.search_api import SearchAPIClient
            search_client = SearchAPIClient()
            
            linkedin_url = await search_client.search_linkedin_profile(name, context)
            
            # If found, try to scrape profile
            profiles = []
            if linkedin_url:
                # In Phase 2a, we have LinkedIn scraper
                from ..tasks.enrichment_tasks import scrape_linkedin
                
                # Celery task - would normally be called async
                # For now, return the search result
                profiles = [
                    {
                        "name": name,
                        "url": linkedin_url,
                        "source": "linkedin",
                        "profile_data": {"found_via_search": True}
                    }
                ]
            
            elapsed = datetime.now() - start
            
            return {
                "source": "linkedin",
                "profiles": profiles,
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": len(profiles) > 0,
            }
            
        except Exception as e:
            logger.error(f"LinkedIn query failed: {str(e)}")
            return None
    
    async def _query_instagram(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query Instagram for profiles.
        
        Args:
            name: Person name or username
            context: Optional context
            
        Returns:
            Dict with Instagram results or None
        """
        try:
            start = datetime.now()
            
            from ..scrapers.instagram_scraper import InstagramScraper
            scraper = InstagramScraper()
            
            profile = await scraper.scrape_profile(name)
            
            profiles = []
            if profile:
                profiles = [
                    {
                        "name": name,
                        "url": f"https://instagram.com/{name}",
                        "source": "instagram",
                        "profile_data": profile.__dict__,
                    }
                ]
            
            elapsed = datetime.now() - start
            
            return {
                "source": "instagram",
                "profiles": profiles,
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": len(profiles) > 0,
            }
            
        except Exception as e:
            logger.error(f"Instagram query failed: {str(e)}")
            return None
    
    async def _query_tiktok(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query TikTok for profiles.
        
        Args:
            name: Person name or username
            context: Optional context
            
        Returns:
            Dict with TikTok results or None
        """
        try:
            start = datetime.now()
            
            from ..scrapers.tiktok_scraper import TikTokScraper
            scraper = TikTokScraper()
            
            profile = await scraper.scrape_profile(name)
            
            profiles = []
            if profile:
                profiles = [
                    {
                        "name": name,
                        "url": f"https://tiktok.com/@{name}",
                        "source": "tiktok",
                        "profile_data": profile.__dict__,
                    }
                ]
            
            elapsed = datetime.now() - start
            
            return {
                "source": "tiktok",
                "profiles": profiles,
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": len(profiles) > 0,
            }
            
        except Exception as e:
            logger.error(f"TikTok query failed: {str(e)}")
            return None
    
    async def _query_github(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query GitHub for profiles.
        
        Args:
            name: Person name or GitHub username
            context: Optional context
            
        Returns:
            Dict with GitHub results or None
        """
        try:
            start = datetime.now()
            
            from ..scrapers.github_scraper import GitHubScraper
            scraper = GitHubScraper()
            
            profile = await scraper.scrape_profile(name)
            
            profiles = []
            if profile:
                profiles = [
                    {
                        "name": profile.name or name,
                        "url": f"https://github.com/{name}",
                        "source": "github",
                        "profile_data": {
                            "username": profile.username,
                            "repos": profile.public_repo_count,
                            "followers": profile.follower_count,
                            "stars": profile.total_stars,
                        },
                    }
                ]
            
            elapsed = datetime.now() - start
            
            return {
                "source": "github",
                "profiles": profiles,
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": len(profiles) > 0,
            }
            
        except Exception as e:
            logger.error(f"GitHub query failed: {str(e)}")
            return None
    
    async def _query_twitter(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query Twitter/X for profiles.
        
        Args:
            name: Person name or Twitter handle
            context: Optional context
            
        Returns:
            Dict with Twitter results or None
        """
        try:
            start = datetime.now()
            
            # Twitter requires API access or scraping
            # For now, return None (stub)
            # In Phase 2b, integrate with Twitter API or nitter.net proxy
            
            elapsed = datetime.now() - start
            
            return {
                "source": "twitter",
                "profiles": [],
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": False,
            }
            
        except Exception as e:
            logger.error(f"Twitter query failed: {str(e)}")
            return None
    
    async def _query_search(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query general web search for profiles.
        
        Args:
            name: Person name
            context: Optional context (location, profession, etc.)
            
        Returns:
            Dict with search results or None
        """
        try:
            start = datetime.now()
            
            from ..scrapers.search_api import SearchAPIClient
            search_client = SearchAPIClient()
            
            search_results = await search_client.search_person(name, context or "")
            
            profiles = [
                {
                    "name": name,
                    "url": result.url,
                    "source": "search",
                    "profile_data": {
                        "title": result.title,
                        "snippet": result.snippet,
                        "published_date": result.published_date,
                    }
                }
                for result in search_results
            ]
            
            elapsed = datetime.now() - start
            
            return {
                "source": "search",
                "profiles": profiles,
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": len(profiles) > 0,
            }
            
        except Exception as e:
            logger.error(f"Web search query failed: {str(e)}")
            return None
    
    async def _query_youtube(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query YouTube for channels.
        
        Args:
            name: Person name
            context: Optional context
            
        Returns:
            Dict with YouTube results or None
        """
        try:
            start = datetime.now()
            
            # YouTube requires API access
            # For now, return stub
            
            elapsed = datetime.now() - start
            
            return {
                "source": "youtube",
                "profiles": [],
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": False,
            }
            
        except Exception as e:
            logger.error(f"YouTube query failed: {str(e)}")
            return None
    
    async def _query_bluesky(self, name: str, context: Optional[str] = None) -> Optional[Dict]:
        """Query Bluesky for profiles.
        
        Args:
            name: Person name or Bluesky handle
            context: Optional context
            
        Returns:
            Dict with Bluesky results or None
        """
        try:
            start = datetime.now()
            
            # Bluesky API is available
            # For now, return stub
            
            elapsed = datetime.now() - start
            
            return {
                "source": "bluesky",
                "profiles": [],
                "query_time_ms": int(elapsed.total_seconds() * 1000),
                "success": False,
            }
            
        except Exception as e:
            logger.error(f"Bluesky query failed: {str(e)}")
            return None


async def dispatch_source_queries(
    person_name: str,
    context: Optional[str] = None,
    enabled_sources: Optional[List[str]] = None,
) -> Dict:
    """Convenience function to dispatch to all sources.
    
    Args:
        person_name: Name to search for
        context: Optional context
        enabled_sources: Optional list of specific sources to query
        
    Returns:
        Aggregated results from all sources
    """
    dispatcher = SourceDispatcher()
    return await dispatcher.dispatch_to_sources(person_name, context, enabled_sources)
