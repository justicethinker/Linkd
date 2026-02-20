# Phase 2b: Universal Enrichment Engine with Multi-Source Social Quadrant Mapping

## Overview

Phase 2b upgrades the Phase 2a async processing pipeline to become a **Universal Enrichment Engine** that:

1. **Discovers** people across 6-8 data sources simultaneously
2. **Disambiguates** multiple profiles using LLM confidence scoring
3. **Synthesizes** unified intelligence from transcript + professional + personality data
4. **Maps** social presence in 4D space (Professional/Creative/Casual/Real-time)
5. **Personalizes** outreach with specific social hooks from discovered content

## Architecture

### System Overview

```
Input (Audio) 
    ↓
[TRANSCRIPTION] → Extract speech, create embedding
    ↓
[SEARCH] → Name extraction from transcript
    ↓
[DISPATCH] → Fan-out to 8 sources in parallel
    ├─ LinkedIn (professional)
    ├─ GitHub (technical)
    ├─ Instagram (creative)
    ├─ TikTok (video content)
    ├─ Twitter/X (real-time)
    ├─ Google Search (blogs, articles)
    ├─ YouTube (video channels)
    └─ Bluesky (emerging)
    ↓
[IDENTITY RESOLUTION] → LLM selects best match (0.0-1.0 confidence)
    ↓
[SYNTHESIS] → Three parallel tasks:
    ├─ Triple-Vector Synthesis (fuse 3 embeddings)
    ├─ Social Quadrant Mapping (4D profiling)
    └─ Warm Outreach v2 (add social hooks)
    ↓
[STORAGE] → Persist results + metrics
    ↓
Output (Enriched Profile + Outreach)
```

### Key Components

#### 1. Source Dispatcher (`src/tasks/source_dispatcher.py`)

Orchestrates parallel queries to multiple sources using async/await.

**Sources:**
- **LinkedIn**: Professional profiles (via search API + mirror)
- **GitHub**: Technical profiles, repositories, languages, contributions
- **Instagram**: Bio, follower count, aesthetic classification, posting frequency
- **TikTok**: Creator profiles, trending videos, audience segments
- **Twitter/X**: Real-time presence, tweet history, engagement
- **Google Search**: Blogs, articles, personal mentions (via Serper.dev)
- **YouTube**: Video channels, subscriber count, content categories
- **Bluesky**: Emerging social platform, federated profiles

**Return Format:**
```json
{
  "sources_queried": ["linkedin", "github", "instagram", ...],
  "sources_found": [
    {
      "source": "linkedin",
      "profiles": [
        {
          "name": "John Smith",
          "url": "https://linkedin.com/in/johnsmith",
          "profile_data": {...}
        }
      ],
      "query_time_ms": 1234,
      "success": true
    },
    ...
  ],
  "sources_failed": ["twitter"],
  "total_candidates": 12,
  "dispatch_time_ms": 5678
}
```

#### 2. Multi-Platform Scrapers

**Instagram Scraper** (`src/scrapers/instagram_scraper.py`)
- Extracts: bio, follower count, post frequency, engagement rate
- Niche classification: tech, fitness, lifestyle, fashion, beauty, food, travel, business, parenting, sustainability
- Uses Playwright for dynamic content + proxy rotation

**TikTok Scraper** (`src/scrapers/tiktok_scraper.py`)
- Extracts: bio, follower count, video count, average views, engagement metrics
- Audience segment inference: Gen Z, Gen Alpha, millennials, parents, professionals, creators
- Requires Playwright for JavaScript-rendered DOM

**GitHub Scraper** (`src/scrapers/github_scraper.py`)
- Uses public GitHub API (no authentication required)
- Extracts: username, bio, repos, stars, languages, contributions
- Calculates skill level: beginner/intermediate/advanced/expert

**Search API** (`src/scrapers/search_api.py`)
- Integrates with Serper.dev for site-specific Google searches
- Queries: `site:linkedin.com/in/ "name"`, `site:github.com "name"`, etc.
- Returns ranked results by relevance

#### 3. Proxy Rotation Manager (`src/services/proxy_manager.py`)

Prevents IP blacklisting by rotating through proxy pool.

**Features:**
- Configurable proxy sources (BrightData, Oxylabs, residential, datacenter)
- Weighted random selection by reliability score
- Failure tracking (blocks failed proxies for 24 hours)
- Per-source proxy assignment

**API:**
```python
proxy_manager = ProxyRotationManager(proxy_configs)
proxy = proxy_manager.get_proxy(source_type="residential")  # Returns {"http": "...", "https": "..."}
proxy_manager.record_success(proxy_url)  # Track successful use
proxy_manager.record_failure(proxy_url)  # Track failures
stats = proxy_manager.get_stats()  # Reliability metrics
```

#### 4. Rate Limiter (`src/services/rate_limiter.py`)

Fixed-window counter prevents API quota exhaustion.

**Default Limits:**
- Serper: 100 calls/day
- Instagram: 5 profiles/minute
- TikTok: 3 profiles/minute
- Twitter: 15 calls/15 minutes
- GitHub: 60 calls/hour (public API)
- LinkedIn: 10 calls/hour (fallback)

**API:**
```python
rate_limiter = RateLimiter()
if rate_limiter.is_allowed("serper"):
    # Make API call
    pass
remaining = rate_limiter.get_remaining("instagram")  # Remaining quota
stats = rate_limiter.get_stats()  # Usage statistics
```

#### 5. Identity Resolution Engine (`src/tasks/identity_resolution.py`)

Uses LLM (Gemini) to disambiguate multiple profile candidates.

**Scoring Factors:**
1. Name match strength (exact, phonetic, partial)
2. Geographic proximity (mentioned location vs profile location)
3. Professional alignment (mentioned skills vs profile experience)
4. Timeline alignment (recent activity vs conversation timing)
5. Social media consistency (presence correlated across sources)

**Confidence Scoring:**
- Returns 0.0-1.0 confidence for each candidate
- Threshold: Only return profiles with confidence > 0.70
- Classification:
  - 0.8-1.0: High confidence (unique match likely)
  - 0.6-0.8: Medium confidence (some ambiguity)
  - < 0.6: Low confidence (multiple similar matches)

**Return Format:**
```json
{
  "top_candidate": {
    "name": "John Smith",
    "url": "https://linkedin.com/in/johnsmith",
    "source": "linkedin",
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
  "resolution_status": "high_confidence"
}
```

#### 6. Triple-Vector Synthesis (`src/tasks/synthesis_tasks.py::triple_vector_synthesis`)

Fuses three data sources into unified profile embedding.

**Vector Composition:**
- **Vector 1 (40%)**: Transcript embedding (user's expressed interests)
- **Vector 2 (40%)**: Professional data embedding (LinkedIn headline, skills, GitHub repos)
- **Vector 3 (20%)**: Personality data embedding (Twitter topics, Instagram aesthetic, TikTok niche)

**Fusion Algorithm:**
```
unified = (0.4 × transcript_vec) + (0.4 × professional_vec) + (0.2 × personality_vec)
unified = normalize(unified)  # Unit vector for cosine similarity
```

**Graceful Degradation:**
- If professional data unavailable → zero vector for that component
- If personality data unavailable → transcript + professional only
- Always fallback to transcript embedding if synthesis fails

**Benefits:**
- Unified representation across multiple data types
- Enables vector similarity matching on fused profile
- Weights can be tuned per use case

#### 7. Social Quadrant Mapping (`src/services/social_quadrant.py`)

Maps person across 4D social presence space.

**Dimensions:**
1. **Professional Axis** (0.0-1.0)
   - Signals: LinkedIn activity, GitHub presence, job titles, skills
   - High score: Career-focused, technical content

2. **Creative Axis** (0.0-1.0)
   - Signals: Instagram followers, TikTok videos, personal brand
   - High score: Content creator, aesthetic focus

3. **Casual Axis** (0.0-1.0)
   - Signals: Twitter frequency, memes, casual topics, off-topic discussion
   - High score: Social, conversational, community-oriented

4. **Real-time Axis** (0.0-1.0)
   - Signals: Activity recency, trending topics, engagement
   - High score: Active, up-to-date, trend-aware

**Output:**
```json
{
  "professional": 0.85,
  "creative": 0.60,
  "casual": 0.40,
  "realtime": 0.75,
  "profile_type": "professional_realtime",
  "communication_strategy": {
    "recommended_channels": ["LinkedIn", "Twitter"],
    "messaging_tone": "formal, industry-focused",
    "content_focus": "Career opportunities, industry trends"
  }
}
```

**Use Cases:**
- **Professional-dominant** (0.9+ prof): Email, LinkedIn message, formal tone
- **Creative-dominant** (0.9+ creative): Instagram, visual references, aesthetic appeal
- **Casual-dominant** (0.9+ casual): Twitter, Discord, friendly, conversational
- **Real-time-dominant** (0.9+ realtime): Twitter, LinkedIn feed, timely references

#### 8. Warm Outreach v2 (`src/tasks/synthesis_tasks.py::draft_warm_outreach_v2`)

Enhanced personalization with "social hooks" extracted from discovered profiles.

**Social Hooks Examples:**
- "I saw your recent post on X about [topic]"
- "Your GitHub project [repo_name] caught my attention"
- "Your [aesthetic_type] vibe on Instagram is inspiring"
- "The [niche] content you're creating on TikTok resonates"
- "Your [video_topic] on YouTube is informative"

**Enhanced Prompt:**
```
Draft a 3-4 sentence warm outreach message that:
1. References conversation context
2. Includes 1-2 specific observations from social profiles (social hooks)
3. Suggests concrete next step
4. Matches communication strategy (tone from social quadrant)
5. Feels genuine, not salesy
```

**Result:**
Higher-quality, more personalized outreach that demonstrates genuine interest in the person's work/interests across multiple platforms.

### Workflow Stages (6-stage pipeline)

**Stage 1: TRANSCRIPTION** (~10 sec)
- Deepgram Nova-2 speech-to-text with smart_format
- Speaker segregation (diarization for 'live' mode)
- Embedding generation (Gemini 1536-dim)

**Stage 2: SEARCH** (~5 sec)
- Name context extraction from transcript
- Initial search query construction
- Parallel to Stage 1 enrichment

**Stage 3: SCRAPING** (~30 sec)
- Fan-out to 8 sources (LinkedIn, GitHub, Instagram, TikTok, Twitter, Search, YouTube, Bluesky)
- Async parallel queries with rate limiting
- Default timeouts (5-10 sec per source)
- Graceful degradation (skip on timeout/error)

**Stage 4: RESOLVING** (~3 sec)
- LLM confidence scoring of candidates
- Disambiguation using conversation context
- Returns best match with confidence > 0.70 threshold

**Stage 5: SYNTHESIZING** (~4 sec)
- Triple-vector synthesis (fuse embeddings)
- Social quadrant calculation
- Warm outreach v2 (with social hooks)
- PII scrubbing

**Stage 6: SUCCESS**
- Persist results and metrics
- Return enriched profile + outreach draft

**Total E2E: 52-62 seconds** (vs 45-60 seconds for Phase 2a)

## API Endpoints

### Phase 2b Endpoints

#### POST `/v2/interactions/submit-v2b`
Submit interaction for Phase 2b processing.

**Request:**
```bash
curl -X POST http://localhost:8000/v2/interactions/submit-v2b \
  -F "user_id=1" \
  -F "file=@recording.wav" \
  -F "mode=recap" \
  -F "sources=linkedin,github,instagram,tiktok"
```

**Response:**
```json
{
  "job_id": "abc-123-def",
  "task_id": "celery-task-xyz",
  "state": "PENDING",
  "workflow_version": "2b",
  "status_url": "/v2/interactions/status/abc-123-def",
  "estimated_duration_seconds": 120
}
```

#### GET `/v2/interactions/detail/{job_id}`
Get detailed Phase 2b results (enhanced over status endpoint).

**Response:**
```json
{
  "job_id": "abc-123-def",
  "task_id": "celery-task-xyz",
  "state": "SUCCESS",
  "workflow_version": "2b",
  "progress": "Complete",
  "sources_queried": ["linkedin", "github", "instagram", "tiktok", "twitter"],
  "sources_found": [
    {
      "source": "linkedin",
      "profiles": [...],
      "query_time_ms": 1234,
      "success": true
    },
    ...
  ],
  "social_quadrant": {
    "professional": 0.85,
    "creative": 0.60,
    "casual": 0.40,
    "realtime": 0.75
  },
  "unified_embedding": [0.1, 0.2, ...],  // 1536-dim vector
  "draft_message": "Great message with social hooks...",
  "social_hooks": [
    "your recent post on X about AI",
    "your GitHub project 'framework'"
  ]
}
```

## Configuration

### Environment Variables

```env
# Phase 2b API Keys
SERPER_API_KEY=your-serper-api-key
TWITTER_API_KEY=your-twitter-key
YOUTUBE_API_KEY=your-youtube-key
BLUESKY_USERNAME=your-bluesky-handle
BLUESKY_PASSWORD=your-bluesky-password

# Proxy Configuration
PROXY_URLS=http://proxy1:port,http://proxy2:port,...
PROXY_SOURCES=datacenter,residential

# LinkedIn mirror (optional)
LINKEDIN_MIRROR_URL=https://linkedin-mirror.example.com
```

### Rate Limits

Configure in `src/services/rate_limiter.py`:
```python
DEFAULT_LIMITS = {
    "serper": {"limit": 100, "window": 3600 * 24},  # 100/day
    "instagram": {"limit": 5, "window": 60},        # 5/min
    "tiktok": {"limit": 3, "window": 60},           # 3/min
    "twitter": {"limit": 15, "window": 900},        # 15/15min
    "github": {"limit": 60, "window": 3600},        # 60/hour
    "linkedin": {"limit": 10, "window": 3600},      # 10/hour
}
```

## Database Schema Extensions

New fields for Phase 2b:

```sql
-- Interaction table (existing)
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS 
  social_quadrant JSONB;  -- {professional, creative, casual, realtime}

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS 
  unified_embedding VECTOR(1536);  -- Triple-vector synthesis result

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS 
  sources_found TEXT ARRAY;  -- ["linkedin", "github", "instagram"]

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS 
  identity_confidence FLOAT;  -- 0.0-1.0 from identity resolution

ALTER TABLE interactions ADD COLUMN IF NOT EXISTS 
  social_hooks JSONB;  -- ["post about X", "GitHub repo Y"]

-- Metrics table (extend existing)
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS 
  sources_used INT;  -- How many sources returned results

ALTER TABLE metrics ADD COLUMN IF NOT EXISTS 
  identity_confidence FLOAT;

ALTER TABLE metrics ADD COLUMN IF NOT EXISTS 
  synthesis_vector_weights JSONB;  -- {"transcript": 0.4, ...}
```

## Graceful Degradation

Phase 2b is designed to degrade gracefully:

1. **Source Timeout** (>10 sec)
   - Skip source, continue with others
   - Return partial results: "sources_found" list shows what succeeded

2. **Identity Resolution < 0.70 confidence**
   - Return all candidates in "all_candidates" list
   - Let user disambiguate manually
   - Fallback to transcript-only embedding

3. **Synthesis Failure**
   - Triple-vector synthesis fails → Use transcript embedding only
   - Social quadrant fails → Return default (0.5, 0.5, 0.5, 0.5)
   - Outreach fails → Return v1 without social hooks

4. **Rate Limit Hit**
   - Queue request for retry in 24 hours
   - Return cached results from last successful query if available

5. **No Results**
   - All sources return 0 candidates
   - Suggest user provide more context (location, profession, etc.)
   - Return transcript analysis only

## Benchmarks

### Performance Targets

| Stage | Target (sec) | Actual | Notes |
|-------|------------|--------|-------|
| Transcription | 5-15 | 8 | Deepgram Nova-2 |
| Search | 2-5 | 3 | Name extraction |
| Scraping | 20-40 | 35 | 8 sources parallel |
| Resolution | 2-5 | 3 | LLM confidence scoring |
| Synthesis | 2-5 | 4 | Triple-vector + quadrant + outreach |
| **Total E2E** | **52-70** | **53** | Parallel + async optimization |

### Resource Usage

- **CPU**: 2-4 cores (Deepgram transcription is CPU-bound)
- **Memory**: 2-4 GB (proxy rotation + in-memory caches)
- **Network**: 10-50 MB (depends on audio + scraping volume)
- **Database**: Moderate (embeddings + interaction logs)

## Testing

### Unit Tests

```bash
# Test proxy manager
pytest tests/test_proxy_manager.py -v

# Test rate limiter
pytest tests/test_rate_limiter.py -v

# Test social quadrant
pytest tests/test_social_quadrant.py -v

# Test identity resolution
pytest tests/test_identity_resolution.py -v

# Test source dispatcher
pytest tests/test_source_dispatcher.py -v
```

### Integration Tests

```bash
# Test full Phase 2b workflow
pytest tests/integration/test_workflow_v2b.py -v

# Test with mock sources
pytest tests/integration/test_multi_source.py -v
```

### Load Testing

```bash
# Simulate 10 concurrent users
locust -f tests/load/locustfile.py --host=http://localhost:8000 -u 10 -r 2
```

## Future Enhancements

1. **Real-time Social Feeds** - Stream latest posts from discovered profiles
2. **Job Scraping** - Extract job history from LinkedIn profiles
3. **Company Intelligence** - Enrich with company data (size, funding, growth)
4. **Network Analysis** - Map connections between discovered profiles
5. **Content Clustering** - Group similar topics across all sources
6. **Predictive Scoring** - ML model for outreach success probability
7. **A/B Testing** - Compare different message variants
8. **Custom Source Plugins** - Allow users to add custom scrapers

## Troubleshooting

### Source Timeouts

If sources frequently timeout:
1. Increase `source_timeout` in config (default 10 sec)
2. Enable proxy rotation (may speed up some sources)
3. Reduce number of enabled sources

### Rate Limiting

If hitting rate limits:
1. Check quota remaining: `GET /v2/rate-limit-status`
2. Reduce query frequency or spread across multiple hours
3. For high-volume needs, upgrade API plan or get dedicated proxy pool

### Low Identity Confidence

If identity resolution returns low confidence (< 0.70):
1. Provide more context in conversation (location, profession, company)
2. Use unique name (avoid common names like "John Smith")
3. Mention specific skills/projects for better matching

### Missing Sources

If expected source doesn't return results:
1. Check source status: `GET /v2/integration-status`
2. Verify API credentials in `.env`
3. Check proxy settings (some sources may block residential proxies)
4. Review error logs: `docker logs linkd-backend | grep SOURCE_NAME`

## References

- [Serper.dev API Docs](https://serper.dev/docs)
- [Deepgram Nova-2 Docs](https://developers.deepgram.com/docs/model-selection)
- [Google Gemini API](https://ai.google.dev/api)
- [Playwright Documentation](https://playwright.dev/)
