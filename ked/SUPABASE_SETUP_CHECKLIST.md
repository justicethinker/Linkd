# Supabase Integration Deployment Checklist

## Step 1: Install Dependencies

```bash
cd /workspaces/Linkd/ked
pip install -r requirements.txt
```

**Verification**:
```bash
python -c "import supabase; print('✓ Supabase installed')"
```

---

## Step 2: Configure Environment Variables

### Local Development (.env file)

```bash
# From Supabase Dashboard → Settings → API
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Railway Production

1. Go to **Railway Dashboard**
2. Select your project
3. Go to **Settings → Shared Variables**
4. Add these variables:
   ```
   SUPABASE_URL = https://your-project.supabase.co
   SUPABASE_ANON_KEY = <your-anon-key>
   SUPABASE_SERVICE_ROLE_KEY = <your-service-role-key>
   ```

---

## Step 3: Create Supabase Resources

### A. Create Database Tables

Go to **Supabase Dashboard → SQL Editor** and run:

```sql
-- Create user_profiles table
create table if not exists user_profiles (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  unique(user_id)
);

-- Create recordings table  
create table if not exists recordings (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  recording_id uuid not null,
  mode text not null check (mode in ('live', 'recap')),
  duration_seconds integer not null check (duration_seconds > 0),
  file_size integer not null,
  storage_url text not null,
  status text default 'uploaded' check (status in ('uploaded', 'processing', 'completed', 'failed')),
  metadata jsonb,
  job_id uuid,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  unique(user_id, recording_id)
);

-- Create indexes
create index idx_user_profiles_user_id on user_profiles(user_id);
create index idx_recordings_user_id on recordings(user_id);
create index idx_recordings_status on recordings(status);
create index idx_recordings_created_at on recordings(created_at desc);
```

### B. Create Storage Bucket

In **Supabase Dashboard → Storage**:

1. Click **+ New bucket**
2. Name: `recordings`
3. Visibility: **Private**
4. Click **Create bucket**

### C. Enable Row-Level Security

In **Supabase Dashboard → SQL Editor**, run:

```sql
-- Enable RLS on tables
alter table user_profiles enable row level security;
alter table recordings enable row level security;

-- Policies for user_profiles
create policy "Users can view own profile"
  on user_profiles for select
  using (auth.uid() = user_id);

create policy "Users can insert own profile"
  on user_profiles for insert
  with check (auth.uid() = user_id);

create policy "Users can update own profile"
  on user_profiles for update
  using (auth.uid() = user_id);

-- Policies for recordings
create policy "Users can view own recordings"
  on recordings for select
  using (auth.uid() = user_id);

create policy "Users can insert recordings"
  on recordings for insert
  with check (auth.uid() = user_id);

create policy "Users can update own recordings"
  on recordings for update
  using (auth.uid() = user_id);

create policy "Users can delete own recordings"
  on recordings for delete
  using (auth.uid() = user_id);

-- Storage policies
create policy "Authenticated users can upload recordings"
  on storage.objects for insert
  to authenticated
  with check (bucket_id = 'recordings');

create policy "Users can access own recordings"
  on storage.objects for select
  to authenticated
  using (bucket_id = 'recordings' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "Users can delete own recordings"
  on storage.objects for delete
  to authenticated
  using (bucket_id = 'recordings' and auth.uid()::text = (storage.foldername(name))[1]);
```

---

## Step 4: Test the Integration

### A. Start the Backend

```bash
cd /workspaces/Linkd/ked
python -m uvicorn src.main:app --reload
```

Expected output:
```
✓ Linkd backend started (development mode)
✓ Database initialized successfully
```

### B. Test Ingest Service Status (No Auth Required)

```bash
curl http://localhost:8000/ingest/status
```

Expected response:
```json
{
  "success": true,
  "service": "ingest",
  "status": "ready",
  "max_upload_size_mb": 50,
  "supported_formats": ["wav", "mp3", "ogg"]
}
```

### C. Get Supabase JWT Token

Use Supabase client to sign in:

```bash
# Using Supabase CLI (if installed)
supabase auth test-user --password yourpassword

# Or via JavaScript/Python client library
```

Example in Python:
```python
from supabase import create_client

client = create_client(
    "https://your-project.supabase.co",
    "your-anon-key"
)

# Sign up or sign in
response = client.auth.sign_up(
    {"email": "test@example.com", "password": "password123"}
)

token = response.session.access_token
print(f"Token: {token}")
```

### D. Test Protected Ingest Endpoint

```bash
# 1. Create a test audio file
ffmpeg -f lavfi -i sine=f=440:d=5 -q:a 9 -acodec libmp3lame -ac 1 -ar 22050 test.wav

# 2. Upload to ingest endpoint
TOKEN="your-supabase-jwt-token"

curl -X POST http://localhost:8000/ingest/audio \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.wav" \
  -F "mode=recap" \
  -F "duration_seconds=5"
```

Expected response:
```json
{
  "success": true,
  "recording_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "storage_url": "https://project.supabase.co/storage/...",
  "message": "Audio ingested successfully"
}
```

### E. Test Authentication Protection

Try without token (should fail with 401):
```bash
curl -X POST http://localhost:8000/ingest/audio \
  -F "file=@test.wav"
```

Expected response:
```json
{
  "detail": "Missing authentication token"
}
```

---

## Step 5: Verify Database & Storage

### A. Check Database Records

In **Supabase Dashboard → SQL Editor**:

```sql
select * from recordings;
```

Should show your uploaded recording with all metadata.

### B. Check Storage Files

In **Supabase Dashboard → Storage → recordings**:

You should see files organized as:
```
recordings/
└── {user_id}/
    └── recordings/
        └── {recording_id}.wav
```

---

## Step 6: Deploy to Railway

### A. Add Environment Variables

In Railway Dashboard:

1. Go to your project
2. **Settings → Shared Variables** (or Variables tab)
3. Add:
   ```
   SUPABASE_URL=<from-supabase-dashboard>
   SUPABASE_ANON_KEY=<from-supabase-dashboard>
   SUPABASE_SERVICE_ROLE_KEY=<from-supabase-dashboard>
   ```

### B. Deploy

```bash
git add .
git commit -m "Add Supabase integration with protected ingest endpoint"
git push origin main
```

Railway will automatically deploy.

### C. Verify Production Deployment

```bash
# Get your Railway domain/URL
curl https://your-railway-app.up.railway.app/ingest/status
```

---

## Verification Checklist

- [ ] Supabase library installed (`pip install supabase`)
- [ ] Environment variables configured (SUPABASE_URL, SUPABASE_ANON_KEY)
- [ ] Database tables created (user_profiles, recordings)
- [ ] Storage bucket created (recordings)
- [ ] RLS policies enabled
- [ ] `/ingest/status` endpoint returns 200 OK
- [ ] `/ingest/audio` endpoint requires authentication (401 without token)
- [ ] Token authentication works (201 with valid token)
- [ ] Files uploaded to Supabase storage
- [ ] Database records created for uploads
- [ ] Railway environment variables configured
- [ ] Production deployment working

---

## Troubleshooting

### "Supabase configuration missing"

```bash
# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Verify in .env file
cat .env | grep SUPABASE
```

### "Invalid authentication token"

- Token expired? Get a new one from Supabase auth
- Token from different project? Check URLs match
- Decode token to verify: `jwt.io`

### "Storage permission denied"

- Check RLS policies are enabled
- Ensure `authenticated` role can upload

### Files not appearing in storage

1. Check upload response has `storage_url`
2. Verify bucket name is `recordings`
3. Check file path format: `{user_id}/recordings/{id}.wav`

---

## Summary

✅ **Components Integrated**:
- Supabase client initialization
- JWT authentication protection
- Storage upload/download/delete
- Database CRUD operations
- RLS policies for security
- Protected ingest endpoint

✅ **Endpoints Available**:
- `POST /ingest/audio` - Ingest audio with Supabase auth
- `GET /ingest/recording/{id}` - Get recording metadata
- `GET /ingest/recordings` - List user's recordings
- `DELETE /ingest/recording/{id}` - Delete recording
- `GET /ingest/status` - Health check (no auth)

✅ **Ready for Production**:
- All endpoints secured with JWT
- Database schema with RLS
- Storage policies configured
- Error handling implemented
- Logging in place

**Next Steps**:
1. Implement frontend Supabase auth integration
2. Create audio recording UI with offline support
3. Setup Celery tasks for audio processing
4. Add metrics/monitoring for storage usage

