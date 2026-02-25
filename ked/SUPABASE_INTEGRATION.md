# Supabase Integration & Protected Ingest Endpoint

## Overview

This document describes the Supabase integration for storage and database operations, along with the protected ingest endpoint implementation.

## Components

### 1. **Supabase Client Module** (`src/supabase_client.py`)

Central module for managing Supabase operations with authentication and helper classes.

#### Classes

**`SupabaseManager`** - Singleton pattern for Supabase client management
```python
get_client() -> Client          # Get or create Supabase client
reset()                          # Reset client (for testing)
```

**`SupabaseStorage`** - Helper for storage operations
```python
upload_file()                    # Upload file to Supabase storage
delete_file()                    # Delete file from storage
get_file()                       # Download file from storage
get_public_url()                 # Get public URL of file
```

**`SupabaseDatabase`** - Helper for database operations
```python
get_user_profile()               # Get user profile from database
create_user_profile()            # Create new user profile
update_user_profile()            # Update user profile
insert()                         # Generic insert operation
query()                          # Generic query operation
```

#### Dependencies (for FastAPI)

```python
@Depends(verify_supabase_token)       # Verify JWT from Authorization header
@Depends(get_current_user)            # Get user ID from token
@Depends(get_current_user_data)       # Get full user data
@Depends(get_supabase_storage)        # Get SupabaseStorage instance
@Depends(get_supabase_database)       # Get SupabaseDatabase instance
```

---

### 2. **Protected Ingest Endpoint** (`src/routers/ingest.py`)

Secure endpoint for audio ingestion with full Supabase integration.

#### Authentication

All endpoints (except `/ingest/status`) require Supabase JWT authentication:

```bash
curl -X POST http://localhost:8000/ingest/audio \
  -H "Authorization: Bearer $SUPABASE_JWT_TOKEN" \
  -F "file=@recording.wav" \
  -F "mode=recap"
```

#### Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/ingest/audio` | POST | ✅ | Upload and ingest audio |
| `/ingest/recording/{id}` | GET | ✅ | Get recording metadata |
| `/ingest/recordings` | GET | ✅ | List user's recordings |
| `/ingest/recording/{id}` | DELETE | ✅ | Delete recording |
| `/ingest/status` | GET | ❌ | Health check |

#### POST `/ingest/audio` - Upload Audio

**Authentication**: Required (Bearer token)

**Request**:
```bash
curl -X POST http://localhost:8000/ingest/audio \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@meeting.wav" \
  -F "mode=recap" \
  -F "duration_seconds=120" \
  -F "metadata={'topic': 'product planning'}"
```

**Parameters**:
- `file` (required): Audio file (WAV, MP3, OGG)
- `mode` (required): `live` or `recap`
- `duration_seconds` (required): Recording duration (1-3600 seconds)
- `metadata` (optional): JSON metadata (max 20 items)

**Response** (201 Created):
```json
{
  "success": true,
  "recording_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid-from-supabase",
  "storage_url": "https://project.supabase.co/storage/...",
  "job_id": null,
  "message": "Audio ingested successfully"
}
```

#### GET `/ingest/recording/{recording_id}` - Get Recording

**Authentication**: Required (Bearer token)

**Query Parameters**: 
- `recording_id` (required): Recording UUID

**Response**:
```json
{
  "success": true,
  "data": {
    "user_id": "...",
    "recording_id": "...",
    "mode": "recap",
    "duration_seconds": 120,
    "file_size": 2048000,
    "storage_url": "...",
    "status": "uploaded",
    "metadata": {...},
    "created_at": "2024-02-24T10:30:00Z",
    "updated_at": "2024-02-24T10:30:00Z"
  }
}
```

#### GET `/ingest/recordings` - List Recordings

**Authentication**: Required (Bearer token)

**Query Parameters**:
- `status_filter` (optional): Filter by status (uploaded, processing, completed, failed)
- `limit` (optional): Max results 1-100 (default 50)

**Response**:
```json
{
  "success": true,
  "count": 5,
  "data": [
    {
      "recording_id": "...",
      "mode": "recap",
      "duration_seconds": 120,
      "storage_url": "...",
      "status": "uploaded",
      "created_at": "2024-02-24T10:30:00Z"
    },
    ...
  ]
}
```

#### DELETE `/ingest/recording/{recording_id}` - Delete Recording

**Authentication**: Required (Bearer token)

**Response**:
```json
{
  "success": true,
  "message": "Recording deleted successfully"
}
```

#### GET `/ingest/status` - Health Check

**Authentication**: Not required

**Response**:
```json
{
  "success": true,
  "service": "ingest",
  "status": "ready",
  "max_upload_size_mb": 50,
  "supported_formats": ["wav", "mp3", "ogg"]
}
```

---

## Configuration

### Environment Variables

Add to `.env` or Railway environment:

```env
# Supabase Configuration - REQUIRED
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here  # Optional, for admin operations
```

### Where to Get Credentials

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/)
2. Select your project
3. Navigate to **Settings → API**
4. Find:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY` (optional)

### Railway Integration

Supabase credentials are stored in Railway shared variables:

```bash
# In Railway UI:
# 1. Go to your project
# 2. Settings → Shared Variables
# 3. Add/view SUPABASE_URL and SUPABASE_ANON_KEY
```

**Automatic Loading**: The `config.py` Settings class loads these from environment variables automatically.

---

## Database Schema

### Required Tables

Create these tables in Supabase SQL Editor:

#### `user_profiles`
```sql
create table user_profiles (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id),
  email text not null,
  display_name text,
  created_at timestamp default now(),
  updated_at timestamp default now(),
  unique(user_id)
);
```

#### `recordings`
```sql
create table recordings (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id),
  recording_id uuid not null,
  mode text not null check (mode in ('live', 'recap')),
  duration_seconds integer not null,
  file_size integer not null,
  storage_url text not null,
  status text default 'uploaded' check (status in ('uploaded', 'processing', 'completed', 'failed')),
  metadata jsonb,
  job_id uuid,
  created_at timestamp default now(),
  updated_at timestamp default now(),
  unique(user_id, recording_id)
);

create index idx_recordings_user_id on recordings(user_id);
create index idx_recordings_status on recordings(status);
```

### Storage Buckets

Create this bucket in Supabase Storage:

- **Name**: `recordings`
- **Visibility**: `Private` (RLS policies handle access)
- **Path**: `{user_id}/recordings/{recording_id}.wav`

---

## Authentication Flow

### 1. User Signup/Login
```
Client App
    ↓
Supabase Auth (client.auth.signUp/signIn)
    ↓
JWT Token generated
    ↓
Store in local storage
```

### 2. Protected Endpoint Request
```
Client: Authorization: Bearer $JWT_TOKEN
    ↓
Backend: verify_supabase_token dependency
    ↓
Supabase: client.auth.get_user(token)
    ↓
Extract user_id and email
    ↓
Execute endpoint with user context
```

### 3. Token Verification
```python
# In supabase_client.py
response = client.auth.get_user(token)  # Validates with Supabase
if not response or not response.user:
    raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Usage Examples

### Python Client (Using Requests)

```python
import requests

# 1. Get Supabase JWT token (from auth.signInWithPassword or auth.signUp)
# token = "jwt-from-supabase-auth"

# 2. Upload audio
headers = {"Authorization": f"Bearer {token}"}
files = {"file": open("recording.wav", "rb")}
data = {
    "mode": "recap",
    "duration_seconds": 120,
    "metadata": '{"topic": "meeting"}'
}

response = requests.post(
    "http://localhost:8000/ingest/audio",
    headers=headers,
    files=files,
    data=data
)

result = response.json()
print(f"Recording ID: {result['recording_id']}")
print(f"Storage URL: {result['storage_url']}")

# 3. List recordings
response = requests.get(
    "http://localhost:8000/ingest/recordings?status_filter=uploaded",
    headers=headers
)

recordings = response.json()
for rec in recordings['data']:
    print(f"{rec['recording_id']}: {rec['duration_seconds']}s")
```

### JavaScript/TypeScript Client

```typescript
import { createClient } from '@supabase/supabase-js'

// Initialize Supabase
const supabase = createClient(
  'https://your-project.supabase.co',
  'your-anon-key'
)

// 1. Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
})
const token = data.session.access_token

// 2. Upload audio
const formData = new FormData()
formData.append('file', audioBlob, 'recording.wav')
formData.append('mode', 'recap')
formData.append('duration_seconds', '120')

const response = await fetch('http://localhost:8000/ingest/audio', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})

const result = await response.json()
console.log('Recording ID:', result.recording_id)
```

---

## Error Handling

### Authentication Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 401 | Missing authentication token | No Authorization header |
| 401 | Invalid authentication token | Token invalid/expired |
| 403 | Access denied | User not authorized |

### Validation Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | Invalid audio format | File type not supported |
| 400 | Invalid mode | Mode not 'live' or 'recap' |
| 413 | File too large | Exceeds MAX_UPLOAD_SIZE_MB |
| 422 | Validation error | Invalid request parameters |

### Server Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 500 | Failed to ingest audio | Server-side error |
| 503 | Service unavailable | Supabase or storage issue |

---

## Security

### Row-Level Security (RLS)

Enable RLS on `recordings` table:

```sql
-- Enable RLS
alter table recordings enable row level security;

-- Users can only see their own recordings
create policy "Users can view own recordings"
  on recordings for select
  using (auth.uid() = user_id);

create policy "Users can insert own recordings"
  on recordings for insert
  with check (auth.uid() = user_id);

create policy "Users can update own recordings"
  on recordings for update
  using (auth.uid() = user_id);

create policy "Users can delete own recordings"
  on recordings for delete
  using (auth.uid() = user_id);
```

### Storage Policies

Enable RLS on `recordings` bucket:

```sql
-- Only authenticated users can upload
create policy "Authenticated users can upload"
  on storage.objects for insert
  with check (bucket_id = 'recordings' and auth.role() = 'authenticated');

-- Users can only access their own files
create policy "Users can access own files"
  on storage.objects for select
  using (bucket_id = 'recordings' and auth.uid()::text = (storage.foldername(name))[1]);
```

### JWT Token Security

- Tokens are validated against Supabase's public key
- Tokens include expiration time
- Tokens are signed and cannot be forged
- Always use HTTPS in production

---

## Monitoring

### Check Ingest Service Status

```bash
curl http://localhost:8000/ingest/status
```

Response:
```json
{
  "success": true,
  "service": "ingest",
  "status": "ready",
  "max_upload_size_mb": 50,
  "supported_formats": ["wav", "mp3", "ogg"]
}
```

### View Logs

```bash
# Terminal where FastAPI is running shows logs:
[2024-02-24 10:30:00] INFO - [user-uuid] Ingesting audio: recording-uuid (2048000 bytes, recap)
[2024-02-24 10:30:05] INFO - [user-uuid] Uploaded to storage: https://...
[2024-02-24 10:30:06] INFO - [user-uuid] Created database record: recording-uuid
```

### Monitor Storage

Check Supabase Storage:
1. Go to Supabase Dashboard
2. Navigate to **Storage → recordings**
3. View files organized by `{user_id}/recordings/`

---

## Troubleshooting

### "Supabase configuration missing" Error

```
ValueError: Supabase URL and anon key must be configured in environment variables
```

**Solution**: Add to `.env` or Railway environment:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-key
```

### "Invalid authentication token" Error

```
HTTPException: Invalid authentication token
```

**Causes**:
- Token expired (refresh needed)
- Token invalid/malformed
- Token from different Supabase project

**Solution**: Get new token via `auth.signIn()` or refresh token

### "File too large" Error

```
ValidationError: File too large: 150.0MB. Maximum: 50MB
```

**Solution**: 
- Use chunked upload for files > 50MB
- Or increase `MAX_UPLOAD_SIZE_MB` in `.env`

### Storage Upload Fails

```
Failed to upload file: Storage error
```

**Causes**:
- Bucket doesn't exist
- RLS policy blocks upload
- Insufficient storage quota

**Solution**:
1. Verify `recordings` bucket exists
2. Check RLS policies allow authenticated uploads
3. Check Supabase storage quota

---

## Summary

✅ **Components Created**:
- ✅ `src/supabase_client.py` - Supabase client management and helpers (370 lines)
- ✅ `src/routers/ingest.py` - Protected ingest endpoints (350 lines)
- ✅ Updated `src/config.py` - Supabase configuration
- ✅ Updated `requirements.txt` - Added `supabase==2.4.0`
- ✅ Updated `.env.example` - Supabase credentials template

**Status**: ✅ Ready for deployment

**Next Steps**:
1. Add Supabase credentials to Railway environment variables
2. Create tables and storage bucket in Supabase
3. Enable RLS policies on database and storage
4. Test ingest endpoints with Supabase authentication
5. Integrate with frontend using Supabase client library

