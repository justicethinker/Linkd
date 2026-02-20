# Phase 2: Distributed Task Pipeline
## The Scaling & Enrichment Layer

**Status**: In Development | **Target**: Production-ready distributed system

---

## Overview

Phase 2 transforms the synchronous Phase 1 API into a **Distributed Task Pipeline** using Celery + Redis. Every interaction is now a workflow that fans out across multiple parallel tasks:

```
User uploads audio
    ↓
    ├─→ TRANSCRIPTION (Deepgram Nova-2)
    ├─→ EMBEDDING (Gemini embedding-001)
    ├─→ STORE_CONVERSATION (Database)
    ↓
    ├─→ ENRICHMENT (parallel):
    │   ├─ NAME_EXTRACTION (Gemini LLM)
    │   ├─ SCRAPE_LINKEDIN (Selenium + Circuit Breaker)
    │   └─ SCRAPE_TWITTER (fallback)
    ├─→ PII_SCRUBBING (regex anonymization)
    ↓
    ├─→ SYNTHESIS (parallel):
    │   ├─ RECURSIVE_INSIGHT (Gemini + context fusion)
    │   └─ WARM_OUTREACH (draft personalized message)
    ↓
    └─→ STORE_METRICS (database persistence)
```

---

## System Architecture

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Message Broker** | Redis | In-memory queue for task distribution |
| **Task Queue** | Celery | Orchestrates workflows and dependencies |
| **Transcription Pool** | Multiprocessing | CPU-optimized for Deepgram processing |
| **Enrichment Pool** | Gevent | I/O-optimized for web scraping |
| **Monitoring** | Flower | Real-time task dashboard (port 5555) |
| **Result Backend** | Redis DB 1 | Stores task results and state |
| **Application Cache** | Redis DB 2 | Temporary data and circuit breaker state |

### Queue Priority

```
Transcription Queue:
  - Priority 10 (highest)
  - transcribe_audio, embed_interests, store_conversation
  - Pool: multiprocessing (4 workers)
  - Timeout: 10 minutes (hard limit)

Enrichment Queue:
  - Priority 5 (medium)
  - extract_name_context, scrape_linkedin, scrape_twitter, scrub_pii
  - Pool: Gevent (16 workers for I/O concurrency)
  - Timeout: 30 minutes (web scraping can be slow)

Default Queue:
  - Priority 0 (lowest)
  - generic, utility tasks
  - Pool: multiprocessing (shared)
```

---

## Core Features

### 1. Task Orchestration (Celery Chains & Chords)

**Chains** define sequential dependencies:
```python
Chain(
    transcribe_audio.s(),
    embed_interests.s(),
    store_conversation.s(),
)
```

**Chords** enable fork-join parallelism:
```python
Chord([
    scrape_linkedin.s(),
    scrub_pii.s(),
]).apply_async(...)  # Both run in parallel
```

### 2. Resilience Patterns

#### Retry Logic
All tasks have exponential backoff:
```python
autoretry_for = (Exception,)
retry_kwargs = {"max_retries": 5}
retry_backoff = True
retry_backoff_max = 600  # 10 minutes
retry_jitter = True  # Prevent thundering herd
```

#### Circuit Breaker (Scraping Protection)
Prevents IP blacklisting by monitoring CAPTCHA/429 errors:

```python
def trip_circuit_breaker(ip_hash: str, reason: str, duration_hours: int = 1):
    CIRCUIT_BREAKER_STATE[ip_hash] = {
        "blocked_until": datetime.now() + timedelta(hours=duration_hours),
        "reason": reason,
    }
```

If LinkedIn returns CAPTCHA or 429, the circuit is **tripped** for 1 hour, preventing further scraping attempts.

#### PII Scrubbing
Automatically removes sensitive data before storage:
- Phone numbers: `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b`
- Emails: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
- Social Security numbers: `\b\d{3}-\d{2}-\d{4}\b`
- Credit cards: `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b`

### 3. Enrichment Strategy

#### Name Context Extraction
LLM analyzes transcript to create searchable queries:

```json
{
  "persons": [
    {
      "name": "Chidi",
      "search_query": "Chidi Backend Developer Nigeria",
      "confidence": 0.95
    }
  ]
}
```

#### LinkedIn Scraping with Fallback
1. **Primary**: Selenium + BeautifulSoup
2. **Fallback**: Twitter/X public profiles
3. **Last Resort**: Google Search snippet

#### Recursive Synthesis
Final insight combines three data sources:
1. User's persona vector
2. Extracted interests from transcript
3. Scraped social context

Result: Personalized "You both follow Solana projects" insights.

### 4. State Machine

Polling endpoint returns granular progress:

```
PENDING
  ↓
TRANSCRIPTION → Deepgram processing...
EMBEDDING → Creating semantic vector...
ENRICHMENT → Scraping LinkedIn profiles...
SYNTHESIS → Creating personalized insight...
SUCCESS → Complete, results available
  ↓
(or) ERROR at any stage
```

---

## Setup Instructions

### 1. Install Dependencies
```bash
cd /workspaces/Linkd/ked
pip install -r requirements.txt
```

### 2. Start Redis
```bash
redis-server --port 6379
```

### 3. Start Worker Pools
```bash
bash start_workers.sh
```

This starts:
- **Transcription Worker** (4 processes, port logs/transcription.log)
- **Enrichment Worker** (16 gevent workers, logs/enrichment.log)
- **Flower Monitoring** (http://localhost:5555)

### 4. Update .env
```env
REDIS_HOST=localhost
REDIS_PORT=6379
DEEPGRAM_API_KEY=your-key
GEMINI_API_KEY=your-key
```

### 5. Start Backend Server
```bash
uvicorn src.main:app --reload
```

---

## API Endpoints (Phase 2)

### Submit Interaction (Async)
```http
POST /v2/interactions/submit
Content-Type: multipart/form-data

user_id: 1
file: <audio.wav>
mode: "recap"  # or "live"
```

**Response**:
```json
{
  "job_id": "abc-123-def-456",
  "task_id": "celery-task-5f3c9a2b",
  "state": "PENDING",
  "status_url": "/v2/interactions/status/abc-123-def-456"
}
```

### Poll Workflow Status
```http
GET /v2/interactions/status/{job_id}
```

**Response** (during enrichment):
```json
{
  "job_id": "abc-123-def-456",
  "task_id": "celery-task-5f3c9a2b",
  "state": "ENRICHMENT",
  "progress": "Scraping LinkedIn profiles...",
  "result": null
}
```

**Response** (when complete):
```json
{
  "job_id": "abc-123-def-456",
  "task_id": "celery-task-5f3c9a2b",
  "state": "SUCCESS",
  "progress": "Complete",
  "result": {
    "extracted_interests": "React, TypeScript, Solana...",
    "persons": [...],
    "final_insight": {
      "summary": "You both follow Solana projects",
      "overlap_points": ["Blockchain", "Backend Dev", "Web3"],
      "action_items": ["Check GitHub", "Connect on Twitter"]
    },
    "draft_message": "Hey Chidi, I saw you mentioned Solana..."
  }
}
```

### Cancel Workflow
```http
POST /v2/interactions/cancel/{job_id}
```

---

## Monitoring & Debugging

### Flower Dashboard
Open http://localhost:5555 to see:
- **Active Tasks**: Current processing
- **Worker Status**: Health and concurrency
- **Task History**: Success/failure rates
- **Task Detail**: Input, output, timing

### Logs
- `logs/transcription.log` - Deepgram, embedding tasks
- `logs/enrichment.log` - Scraping, name extraction
- `logs/flower.log` - Monitoring system

### Redis CLI
```bash
redis-cli
> KEYS linkd:*
> GET linkd:job:abc-123
```

---

## Performance Benchmarks

| Stage | Est. Duration | Notes |
|-------|---------------|-------|
| Transcription | 5-15 sec | Deepgram Nova-2 |
| Embedding | 1-2 sec | Gemini embedding-001 |
| Name Extraction | 2-3 sec | Gemini LLM |
| LinkedIn Scraping | 10-30 sec | Per profile, with waits |
| PII Scrubbing | <1 sec | Regex patterns |
| Synthesis | 2-4 sec | Gemini recursive inference |
| Total (E2E) | ~30-60 sec | 3-5 profiles typical |

With 2 profiles + no CAPTCHA: **~45 seconds**
Target: **<2 minutes** for full workflow

---

## S3 Lifecycle Policy (Privacy)

Configure bucket policy to auto-delete audio after 48 hours:

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>DeleteRawAudio</ID>
    <Prefix>raw-audio/</Prefix>
    <Status>Enabled</Status>
    <!-- Transition to Glacier after 24 hours -->
    <Transitions>
      <Transition>
        <Days>1</Days>
        <StorageClass>GLACIER_IR</StorageClass>
      </Transition>
    </Transitions>
    <!-- Permanently delete after 48 hours -->
    <Expiration>
      <Days>2</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>
```

---

## Deliverables Tracking

### Infrastructure ✅
- [x] Redis Setup: Broker + Result Backend + Application Cache
- [x] Celery Worker Pool: Transcription (prefork) + Enrichment (gevent)
- [x] Flower Monitoring: Real-time task dashboard
- [x] Polling API: `/v2/interactions/status/{job_id}` with state machine

### Enrichment ✅
- [x] Name-Context Extractor: Gemini LLM analyzes transcript
- [x] Scraper Module: Selenium/BeautifulSoup LinkedIn extraction
- [x] Circuit Breaker: Prevents IP blacklisting on CAPTCHA/429
- [x] Fallback Strategy: Twitter → Google if LinkedIn blocked

### Data Fusion ✅
- [x] Recursive Synthesis: LLM combines persona + transcript + scraped context
- [x] Warm Outreach: Draft personalized message based on overlap

### Privacy ✅
- [x] PII Scrubbing: Remove phone, email, SSN, credit card
- [x] S3 Lifecycle: XML policy for 24h→Glacier, 48h→Delete

---

## Next Steps (Phase 3)

1. **Frontend Integration**: React UI polling `/v2/interactions/status/{job_id}`
2. **Notification System**: Real-time updates via WebSockets
3. **Advanced Matching**: Semantic re-ranking with user feedback loops
4. **Analytics Dashboard**: Task performance, user insights, ROI metrics
5. **Multi-provider Enrichment**: Crunchbase, AngelList, ProductHunt scraping

---

## Troubleshooting

### Workers Not Starting
```bash
# Check Redis
redis-cli PING

# Check Celery config
celery -A src.celery_app inspect active

# Check flower
curl http://localhost:5555/api/workers
```

### Tasks Timing Out
Increase timeout in task decorator:
```python
@app.task(time_limit=1200, soft_time_limit=1100)  # 20 minute hard, 18 minute soft
def long_task():
    pass
```

### CAPTCHA Wall Triggered
The circuit breaker should have tripped. Check Redis:
```bash
redis-cli
> KEYS circuit:*
> TTL circuit:linkedin:default
```

Wait 1 hour, or manually reset:
```bash
> DEL circuit:linkedin:default
```

### Flower Not Loading
Check port 5555 is available and Flower process is running:
```bash
lsof -i :5555
ps aux | grep flower
```

---

## References

- [Celery Documentation](https://docs.celeryproject.io/)
- [Celery Chains & Chords](https://docs.celeryproject.io/en/stable/userguide/canvas.html)
- [Redis Documentation](https://redis.io/docs/)
- [Flower Monitoring](https://flower.readthedocs.io/)
- [Selenium WebDriver](https://www.selenium.dev/documentation/)
- [pgvector for PostgreSQL](https://github.com/pgvector/pgvector)
