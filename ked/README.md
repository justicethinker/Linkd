# ked Backend

The intelligence core of Linkd that manages personal "Anchor Data" and matches it against incoming social interaction data.

## 🏗 Architecture Overview

The backend implements Phase 1 of the Linkd architecture:

### Core Components

1. **Multi-Tenant Foundation**
   - PostgreSQL + pgvector for semantic search
   - Row-Level Security (RLS) for data isolation
   - Vector embeddings (1536-dim with text-embedding-3-small)

2. **Onboarding Router (Persona Ingestion)**
   - **Voice Path**: 60-second professional pitch → Deepgram transcription → LLM persona extraction
   - **LinkedIn Path**: Profile URL → Web scraping → LLM persona extraction
   - Creates weighted "Persona Nodes" (e.g., "React Developer", "AI Enthusiast")

3. **Dual-Mode Networking Pipeline**
   - **Live Mode**: Deepgram Nova-2 with diarization → extract other speaker's interests
   - **Recap Mode**: Deepgram entity extraction → identify contact interests

4. **Vector Synapse (Semantic Matching)**
   - Computes cosine similarity between interaction embeddings and persona vectors
   - Returns top 3 "synapses" (interest overlaps) with similarity > 0.70
   - Persona weights factor into final matching scores

## 🚀 Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ with pgvector extension
- API Keys for:
  - Deepgram (speech-to-text)
  - OpenAI (embeddings & LLM)
  - (Optional) Gemini for alternative LLM processing

### Installation

1. **Copy environment file and add API keys:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and database URL
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database:**
   ```bash
   python init_backend.py
   ```
   
   This will:
   - Create all tables (users, user_persona, interest_nodes, conversations)
   - Apply Row-Level Security policies
   - Execute migration SQL files
   - Create pgvector indexes
   - Register SQL functions for similarity queries

### Running the Server

```bash
uvicorn src.main:app --reload
```

Server will start at: `http://localhost:8000`
- API docs: `http://localhost:8000/docs` (Swagger UI)
- OpenAPI spec: `http://localhost:8000/openapi.json`

## 📁 Project Structure

```
ked/
├── README.md
├── requirements.txt
├── .env.example
├── .env                  # Your local API keys (git-ignored)
├── init_backend.py       # Database initialization script
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI app with lifespan and middleware
│   ├── config.py        # Environment configuration loader
│   ├── db.py            # SQLAlchemy setup, migrations, RLS
│   ├── models.py        # ORM models (User, UserPersona, InterestNode, Conversation)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── onboarding.py     # Persona ingestion endpoints
│   │   └── interactions.py   # Interaction processing endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── deepgram_integration.py   # Speech-to-text & speaker extraction
│   │   ├── linkedin_scraper.py       # LinkedIn profile scraping
│   │   ├── onboarding_service.py     # Persona synthesis via LLM
│   │   └── overlap.py                # Vector similarity matching
│   └── migrations/
│       ├── 001_initial_schema.sql          # Tables, indexes, RLS policies
│       └── 002_similarity_procedures.sql  # SQL functions for vector ops
└── tests/
    └── test_db.py
```

## 🔌 API Endpoints

### Onboarding Routes (`/onboarding`)

#### Create Personas from Voice Pitch
```http
POST /onboarding/voice-pitch
Content-Type: multipart/form-data

user_id: 1
file: <audio_file.wav>
```
Response:
```json
{
  "user_id": 1,
  "personas_created": 5,
  "personas": [
    {"label": "React Developer", "weight": 8},
    {"label": "AI Enthusiast", "weight": 7}
  ]
}
```

#### Create Personas from LinkedIn Profile
```http
POST /onboarding/linkedin-profile
Content-Type: application/x-www-form-urlencoded

user_id=1&profile_url=https://linkedin.com/in/...
```

#### Get User Personas
```http
GET /onboarding/persona?user_id=1
```
Response:
```json
[
  {"id": 1, "user_id": 1, "label": "React Developer", "weight": 8},
  {"id": 2, "user_id": 1, "label": "AI Enthusiast", "weight": 7}
]
```

#### Update a Persona
```http
PATCH /onboarding/persona/1?user_id=1
Content-Type: application/json

{"label": "Senior React Developer", "weight": 9}
```

#### Delete a Persona
```http
DELETE /onboarding/persona/1?user_id=1
```

### Interaction Routes (`/interactions`)

#### Process Recorded Interaction
```http
POST /interactions/process-audio
Content-Type: multipart/form-data

user_id: 1
file: <conversation.wav>
mode: recap
```

Modes:
- `recap`: Entity extraction from entire transcript (diarize=false)
- `live`: Speaker isolation - extract other person's interests (diarize=true)

Response:
```json
{
  "user_id": 1,
  "mode": "recap",
  "extracted_interests": "React, machine learning, cloud architecture...",
  "top_synapses": [
    {"id": 1, "label": "React Developer", "similarity": 0.85},
    {"id": 2, "label": "AI Enthusiast", "similarity": 0.78}
  ],
  "conversation_id": 42
}
```

### Utility Routes

```http
GET /
GET /health
```

## 🔐 Security Features

### Row-Level Security (RLS)
Every query is automatically scoped to the current user via PostgreSQL RLS policies. Set the user context before queries:

```python
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("SET app.current_user_id = 1;"))
    # Now all queries automatically filter by user_id = 1
```

### Vector Indexing
IVFFlat indexes on vector columns for fast cosine similarity search:
```sql
CREATE INDEX idx_user_persona_vector ON user_persona 
  USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
```

## 🧮 SQL Functions

All similarity computations use PostgreSQL functions:

### `compute_top_synapses(user_id, embedding, threshold, limit)`
Returns top interest overlaps with cosine similarity scores.

### `compute_persona_matches(user_id, embedding, threshold, limit)`
Finds personas that match an embedding.

### `compute_weighted_synapses(user_id, embedding, threshold, limit)`
Returns matches weighted by persona importance.

## 📊 Database Schema

### users
- `id` (PK)
- `email` (unique)
- `hashed_password`
- `created_at`

### user_persona (Anchor Data)
- `id` (PK)
- `user_id` (FK, RLS filtered)
- `label` (e.g., "React Developer")
- `weight` (1-10 importance)
- `vector` (1536-dim embedding)

### interest_nodes (Extracted from Interactions)
- `id` (PK)
- `user_id` (FK, RLS filtered)
- `label` (e.g., "Machine Learning")
- `vector` (1536-dim embedding)
- `created_at`

### conversations (Interaction Records)
- `id` (PK)
- `user_id` (FK, RLS filtered)
- `transcript` (extracted interests)
- `metadata` (mode, source, etc.)
- `created_at`

## 🧪 Testing

```bash
pytest tests/
```

Key tests:
- `test_db.py`: Schema creation and RLS policy verification

## 🔄 Logging & Correlation IDs

Every request includes a unique correlation ID (`X-Correlation-ID` header) for tracing:

```
[correlation=abc-123-def] GET /onboarding/persona
[correlation=abc-123-def] Found 3 synapses
```

Logs are structured and include:
- Correlation ID
- User ID (when available)
- Operation (e.g., "Created X personas", "Found Y synapses")
- Detailed error messages

## 🚧 Phase 1 Deliverables Checklist

- [x] PostgreSQL + pgvector enabled
- [x] Multi-tenant schema with RLS
- [x] Data isolation verified
- [x] Voice ingestion (Deepgram)
- [x] LinkedIn scraping
- [x] Persona vectorization (OpenAI embeddings)
- [x] Persona API (GET, PATCH, DELETE)
- [x] Deepgram router (live + recap modes)
- [x] Speaker/entity extraction
- [x] Overlap computation with similarity > 0.70
- [x] E2E onboarding pipeline
- [x] E2E interaction processing
- [x] Structured logging with correlation IDs

## 📝 Example Workflow

```bash
# 1. User 1 records a 60-second pitch
curl -X POST http://localhost:8000/onboarding/voice-pitch \  
  -F "user_id=1" -F "file=@pitch.wav"
# Creates: 5 personas (React, AI, Cloud, etc.)

# 2. User 1 records a conversation with a contact
curl -X POST http://localhost:8000/interactions/process-audio \
  -F "user_id=1" -F "file=@conversation.wav" -F "mode=recap"
# Returns: Top 3 matching personas + suggested follow-up actions

# 3. Update persona weighting based on importance
curl -X PATCH http://localhost:8000/onboarding/persona/1?user_id=1 \
  -H "Content-Type: application/json" \
  -d '{"weight": 10}'
```

## 🐛 Troubleshooting

### "Cannot connect to database"
- Ensure PostgreSQL is running: `psql -U user -d postgres`
- Check `DATABASE_URL` in `.env`
- Verify pgvector extension: `CREATE EXTENSION vector;` in psql

### "Deepgram API errors"
- Verify `DEEPGRAM_API_KEY` is correct in `.env`
- Check audio file format (must be WAV)
- Deepgram docs: https://developers.deepgram.com

### "OpenAI rate limits"
- Check `/openai/api/account` for rate limit usage
- Consider using batching for multiple embedding requests

## 📚 References

- [pgvector Docs](https://github.com/pgvector/pgvector)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org)
- [Deepgram API](https://developers.deepgram.com)
- [OpenAI Embeddings](https://platform.openai.com/docs/api-reference/embeddings)

## 📄 License

Part of the Linkd project.
