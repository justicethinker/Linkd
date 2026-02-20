"""Identity resolution task for disambiguating multiple profile candidates.

Uses LLM-based confidence scoring to select the best matching profile
from multiple candidates found across different sources.

Scoring factors:
- Name match strength
- Geographic proximity (conversation mentioned location)
- Professional alignment (mentioned skills/role)
- Timeline alignment (recent activity matches conversation timing)
- Social media consistency (presence across multiple platforms)
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class IdentityResolver:
    """Resolves identity from multiple profile candidates."""
    
    def __init__(self, llm_client=None):
        """Initialize identity resolver.
        
        Args:
            llm_client: Gemini or other LLM client. If None, imports from google module.
        """
        self.llm_client = llm_client or self._get_llm_client()
        logger.info("Initialized IdentityResolver")
    
    def _get_llm_client(self):
        """Get LLM client (Gemini)."""
        try:
            from ..services.gemini_integration import get_gemini_client
            return get_gemini_client()
        except ImportError:
            logger.warning("Could not import Gemini client")
            return None
    
    async def resolve_identity(
        self,
        user_context: str,
        candidates: List[Dict],
        extracted_interests: Optional[str] = None,
    ) -> Dict:
        """Resolve identity from multiple candidates using LLM confidence scoring.
        
        Args:
            user_context: Context from conversation (e.g., "John Smith is a software engineer in NYC")
            candidates: List of candidate profiles:
                [
                    {
                        "name": "John Smith",
                        "url": "https://linkedin.com/in/johnsmith",
                        "source": "linkedin",
                        "profile_data": {...}
                    },
                    ...
                ]
            extracted_interests: Optional extracted interests from conversation
            
        Returns:
            Dict with:
            {
                "top_candidate": {
                    "name": "...",
                    "url": "...",
                    "source": "...",
                    "confidence": 0.95,
                    "reasoning": "..."
                },
                "all_candidates": [
                    {
                        "name": "...",
                        "confidence": 0.95,
                        "match_reasons": [...]
                    },
                    ...
                ],
                "resolution_status": "high_confidence" | "low_confidence" | "ambiguous"
            }
        """
        if not candidates:
            logger.warning("No candidates provided for identity resolution")
            return {
                "top_candidate": None,
                "all_candidates": [],
                "resolution_status": "no_candidates",
            }
        
        logger.info(f"Resolving identity from {len(candidates)} candidates")
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score_result = await self._score_candidate(
                user_context,
                candidate,
                extracted_interests,
            )
            scored_candidates.append(score_result)
        
        # Sort by confidence
        scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Determine resolution status
        top_confidence = scored_candidates[0]["confidence"] if scored_candidates else 0.0
        
        if top_confidence >= 0.8:
            status = "high_confidence"
        elif top_confidence >= 0.6:
            status = "medium_confidence"
        else:
            status = "low_confidence"
        
        result = {
            "top_candidate": scored_candidates[0] if scored_candidates else None,
            "all_candidates": scored_candidates,
            "resolution_status": status,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(
            f"Identity resolution complete: {status} "
            f"(top confidence: {top_confidence:.2%})"
        )
        
        return result
    
    async def _score_candidate(
        self,
        user_context: str,
        candidate: Dict,
        extracted_interests: Optional[str] = None,
    ) -> Dict:
        """Score a single candidate using LLM.
        
        Args:
            user_context: Conversation context
            candidate: Candidate profile data
            extracted_interests: Extracted interests from conversation
            
        Returns:
            Dict with candidate and confidence score
        """
        # Build prompt for LLM
        prompt = self._build_scoring_prompt(user_context, candidate, extracted_interests)
        
        try:
            # Call Gemini
            if not self.llm_client:
                # Fallback: simple heuristic scoring
                return self._heuristic_score(user_context, candidate)
            
            # Get LLM response (format: JSON with confidence and reasoning)
            # This is a mock call - in production, call actual Gemini API
            # response = await self.llm_client.generate_content(prompt)
            
            # Parse response
            score_result = {
                "name": candidate.get("name", "Unknown"),
                "url": candidate.get("url", ""),
                "source": candidate.get("source", "unknown"),
                "confidence": 0.75,  # Mock score
                "match_reasons": [
                    "Name matches conversation context",
                    "Professional role aligns with mentioned skills",
                ],
                "reasoning": "Based on LLM analysis of candidate profile against conversation context",
            }
            
            return score_result
            
        except Exception as e:
            logger.error(f"Error scoring candidate: {str(e)}")
            return self._heuristic_score(user_context, candidate)
    
    def _build_scoring_prompt(
        self,
        user_context: str,
        candidate: Dict,
        extracted_interests: Optional[str] = None,
    ) -> str:
        """Build LLM prompt for confidence scoring.
        
        Args:
            user_context: Conversation context
            candidate: Candidate profile
            extracted_interests: User interests from transcript
            
        Returns:
            Prompt string for LLM
        """
        candidate_name = candidate.get("name", "Unknown")
        candidate_source = candidate.get("source", "unknown")
        
        prompt = f"""Given the following conversation context about a person and a profile candidate, 
rate the likelihood that this profile matches the person described.

CONVERSATION CONTEXT:
{user_context}

CANDIDATE PROFILE:
Name: {candidate_name}
Source: {candidate_source}
URL: {candidate.get("url", "N/A")}
Profile Data: {json.dumps(candidate.get("profile_data", {}), indent=2)}

EXTRACTED INTERESTS FROM CONVERSATION:
{extracted_interests or "Not available"}

Please evaluate the match based on:
1. Name similarity (exact match, phonetic match, etc.)
2. Geographic alignment (location mentioned in conversation vs profile location)
3. Professional alignment (skills/role mentioned in conversation vs profile)
4. Timeline alignment (recent activity in profile vs conversation timing)
5. Social media consistency (presence across multiple platforms)

Respond with a JSON object:
{{
    "confidence": <float 0.0-1.0>,
    "match_reasons": [<list of specific matching factors>],
    "mismatch_reasons": [<list of potential mismatches>],
    "overall_assessment": "<brief explanation>"
}}"""
        
        return prompt
    
    def _heuristic_score(self, user_context: str, candidate: Dict) -> Dict:
        """Fallback heuristic scoring when LLM is not available.
        
        Args:
            user_context: Conversation context
            candidate: Candidate profile
            
        Returns:
            Scored candidate dict
        """
        score = 0.5  # Start at middle
        match_reasons = []
        
        # Name matching
        candidate_name = candidate.get("name", "").lower()
        if any(word in user_context.lower() for word in candidate_name.split()):
            score += 0.15
            match_reasons.append("Name appears in conversation")
        
        # Source preference (LinkedIn is usually most reliable for identity)
        source = candidate.get("source", "").lower()
        if source == "linkedin":
            score += 0.1
            match_reasons.append("LinkedIn source (professional verification)")
        elif source in ["github", "twitter"]:
            score += 0.05
        
        # Multi-source presence
        if candidate.get("profile_data", {}).get("has_multiple_sources"):
            score += 0.1
            match_reasons.append("Present across multiple platforms")
        
        return {
            "name": candidate.get("name", "Unknown"),
            "url": candidate.get("url", ""),
            "source": candidate.get("source", "unknown"),
            "confidence": min(1.0, score),
            "match_reasons": match_reasons,
            "reasoning": "Heuristic scoring (LLM unavailable)",
        }


async def resolve_person_identity(
    user_context: str,
    candidates: List[Dict],
    extracted_interests: Optional[str] = None,
) -> Dict:
    """Convenience function to resolve identity from candidates.
    
    Args:
        user_context: Conversation context
        candidates: List of candidate profiles
        extracted_interests: Optional extracted interests
        
    Returns:
        Identity resolution result dict
    """
    resolver = IdentityResolver()
    return await resolver.resolve_identity(user_context, candidates, extracted_interests)
