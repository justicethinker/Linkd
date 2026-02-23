"""Workflow orchestration using Celery Chains and Chords.

Defines the complete interaction processing pipeline as a distributed task graph.

The Fan-Out Pattern:
1. transcribe_audio (CPU-bound)
2. embed_interests (depends on transcription)
3. Parallel split:
   - extract_name_context + scrape_linkedin (enrichment - I/O bound)
   - scrub_pii (clean data)
4. Parallel join:
   - recursive_insight (synthesis)
   - draft_warm_outreach (warm outreach)
5. store_metrics (final persistence)
"""

import logging
from celery.canvas import chain, chord
from src.celery_app import app
from src.transcription_tasks import (
    transcribe_audio,
    embed_interests,
    store_conversation,
)
from src.enrichment_tasks import (
    extract_name_context,
    scrape_linkedin,
    scrape_twitter,
)
from src.synthesis_tasks import (
    recursive_insight,
    draft_warm_outreach,
    scrub_pii,
    store_metrics,
)

logger = logging.getLogger(__name__)


def start_interaction_workflow(
    user_id: int,
    job_id: str,
    audio_file_path: str,
    mode: str = "recap",
) -> str:
    """Start the complete interaction processing workflow.
    
    This is the main orchestration function that fans out the workflow:
    
    1. TRANSCRIPTION (sync point)
       transcribe_audio() → embed_interests() → store_conversation()
    
    2. ENRICHMENT (parallel - Chord callback)
       Parallel:
       ├─ extract_name_context() → scrape_linkedin() 
       └─ scrub_pii()
    
    3. SYNTHESIS (parallel in Chord callback)
       Parallel:
       ├─ recursive_insight() → draft_warm_outreach()
       └─ (merge results)
    
    4. PERSISTENCE
       store_metrics()
    
    Args:
        user_id: User ID
        job_id: Job tracking ID
        audio_file_path: Path to audio file
        mode: 'live' or 'recap'
        
    Returns:
        Task ID for monitoring
    """
    logger.info(f"[job_id={job_id}] Starting interaction workflow (user_id={user_id})")
    
    # Transcription chain: Get audio → embed → store
    transcription_chain = chain(
        transcribe_audio.s(user_id, job_id, audio_file_path, mode),
        embed_interests.s(),
        store_conversation.s(),
    )
    
    # Enrichment chord: Run both scraping and PII scrubbing in parallel
    enrichment_chord = chord([
        # Scraping path: Extract names → Scrape LinkedIn → Fallback Twitter
        chain(
            extract_name_context.s(),
            scrape_linkedin.s(),
            scrape_twitter.s(),
        ),
        # PII scrubbing runs independently
        scrub_pii.s(),
    ])
    
    # Synthesis tasks run on aggregated enrichment results
    synthesis_tasks = chord([
        recursive_insight.s(),
        draft_warm_outreach.s(),
    ])
    
    # Complete workflow: Transcription → Enrichment (parallel) → Synthesis → Metrics
    workflow = chain(
        transcription_chain,
        enrichment_chord,
        synthesis_tasks,
        store_metrics.s(),
    )
    
    # Execute the workflow with error handling
    try:
        result = workflow.apply_async()
        logger.info(f"[job_id={job_id}] Workflow started with task_id={result.id}")
        return result.id
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to start workflow: {e}")
        raise


def get_workflow_status(task_id: str) -> dict:
    """Get the current status of a workflow.
    
    Returns metadata about progress and any errors.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Status dict with state, progress, and meta
    """
    try:
        result = app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "state": result.state,
            "progress": result.info.get("progress", "") if isinstance(result.info, dict) else "",
            "meta": result.info,
        }
    except Exception as e:
        logger.error(f"Failed to get workflow status for {task_id}: {e}")
        return {
            "task_id": task_id,
            "state": "ERROR",
            "error": str(e),
        }


def cancel_workflow(task_id: str) -> bool:
    """Cancel a running workflow.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        True if cancelled successfully
    """
    try:
        result = app.AsyncResult(task_id)
        result.revoke(terminate=True)
        logger.info(f"Workflow {task_id} cancelled")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel workflow {task_id}: {e}")
        return False

# ===== Phase 2b Enhancement: Multi-source enrichment workflow =====


def start_interaction_workflow_v2b(
    user_id: int,
    job_id: str,
    audio_file_path: str,
    mode: str = "recap",
    enabled_sources: list = None,
) -> str:
    """Start the Phase 2b interaction processing workflow (multi-source).
    
    Enhanced 6-stage workflow with source dispatcher and identity resolution:
    
    1. TRANSCRIPTION (sync point)
       transcribe_audio() → embed_interests() → store_conversation()
    
    2. SEARCHING (parallel fan-out)
       dispatch_to_sources() + extract_name_context()
    
    3. SCRAPING (parallel - Web scraping + social media)
       Each source scraper runs independently (Instagram, TikTok, GitHub, etc.)
    
    4. RESOLVING (identity resolution)
       resolve_identity() - LLM matches best candidate from multiple results
    
    5. SYNTHESIZING (parallel)
       ├─ triple_vector_synthesis() - Fuse multiple embeddings
       ├─ calculate_social_quadrant() - Map to 4D social space
       ├─ draft_warm_outreach_v2() - Include social hooks
       └─ scrub_pii()
    
    6. PERSISTENCE
       store_metrics()
    
    Args:
        user_id: User ID
        job_id: Job tracking ID
        audio_file_path: Path to audio file
        mode: 'live' or 'recap'
        enabled_sources: Optional list of sources to query (default: all)
        
    Returns:
        Task ID for monitoring
    """
    from .source_dispatcher import dispatch_source_queries
    from .identity_resolution import resolve_person_identity
    from .synthesis_tasks import (
        triple_vector_synthesis,
        calculate_social_quadrant,
        draft_warm_outreach_v2,
    )
    
    logger.info(
        f"[job_id={job_id}] Starting Phase 2b workflow "
        f"(user_id={user_id}, sources={enabled_sources or 'all'})"
    )
    
    # Stage 1: TRANSCRIPTION
    transcription_chain = chain(
        transcribe_audio.s(user_id, job_id, audio_file_path, mode),
        embed_interests.s(),
        store_conversation.s(),
    )
    
    # Stage 2 & 3: SEARCH + SCRAPE (parallel fan-out to all sources)
    search_and_scrape = chord([
        # Source dispatcher: fan-out to 6-8 sources
        # This returns aggregated results from Search, LinkedIn, GitHub, Instagram, TikTok, Twitter, YouTube, Bluesky
        # dispatch_source_queries.s(name, context, sources),
        # For now, use existing enrichment path as foundation
        extract_name_context.s(),
        scrape_linkedin.s(),
        scrape_twitter.s(),
    ])
    
    # Stage 4: RESOLVE (identity resolution)
    # Takes search results and uses LLM to disambiguate
    # resolve_identity.s(user_context, candidates, interests),
    
    # Stage 5: SYNTHESIZE (triple-vector + social quadrant + outreach)
    synthesis_tasks = chord([
        triple_vector_synthesis.s(),
        calculate_social_quadrant.s(),
        draft_warm_outreach_v2.s(),
        scrub_pii.s(),
    ])
    
    # Complete Phase 2b workflow
    workflow = chain(
        transcription_chain,
        search_and_scrape,
        synthesis_tasks,
        store_metrics.s(),
    )
    
    try:
        result = workflow.apply_async()
        logger.info(f"[job_id={job_id}] Phase 2b workflow started with task_id={result.id}")
        return result.id
    except Exception as e:
        logger.error(f"[job_id={job_id}] Failed to start Phase 2b workflow: {e}")
        raise
