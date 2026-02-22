# 📱 Linkd Frontend Architecture

## App Overview

**Linkd** is a professional networking intelligence app that:
1. **Captures User Profile** → Voice pitch or LinkedIn profile
2. **Extracts Personas** → AI-powered persona generation (e.g., "React Developer", "AI Enthusiast")
3. **Records Interactions** → App listens to conversations/calls
4. **Identifies Overlaps** → Matches interaction interests with user personas
5. **Provides Insights** → Shows top matching interests ("Synapses")
6. **Learns from Feedback** → Users approve/reject personas to improve matching

---

## Core Screens & Features

### 1. **Authentication** 
- Sign In / Sign Up
- Password reset
- Firebase Auth integration

### 2. **Onboarding Wizard** (Post-Login)
- **Step 1**: Choose onboarding method
  - Option A: Voice Pitch (60-second professional pitch)
  - Option B: LinkedIn Profile (URL import)
- **Step 2**: Processing indicator with progress
- **Step 3**: Review & Confirm personas generated

### 3. **Dashboard** (Home)
- Welcome message with user's primary persona
- Quick stats:
  - Total personas created
  - Recent interactions count
  - Top matched synapse
- Quick action buttons:
  - Record new interaction
  - Review personas
  - View insights

### 4. **Personas Management**
- List view of all personas with details:
  - Persona name/label
  - Weight (1-10 indicator)
  - Confidence score
  - Created date
- Actions per persona:
  - Approve ✓ (increase weight)
  - Reject ✗ (decrease weight)
  - Rate ⭐ (1-5 stars)
  - View feedback history
- Add/Edit/Delete personas
- Bulk actions

### 5. **Record Interaction**
- Mode selection: "Live" vs "Recap"
  - Live: Diarized conversation (extracts other speaker's interests)
  - Recap: Simple entity extraction from your notes
- Audio recording UI with:
  - Recording timer
  - Waveform visualization
  - Pause/Resume/Stop controls
  - Playback option before submitting
- Submit button with processing indicator

### 6. **Interaction Results**
- Display extracted interests from audio
- Show top 3 "synapses" (matched personas) with:
  - Persona name
  - Similarity score (%)
  - Confidence level
  - Visual progress indicator
- Save interaction
- Log to history

### 7. **Insights / Metrics** 
- Dashboard with KPIs:
  - Total interactions processed
  - Average extraction accuracy
  - Persona approval rate
  - Top performing persona
  - Recent matched synapses
- Charts:
  - Interaction trends (line chart)
  - Persona distribution (pie chart)
  - Accuracy over time

### 8. **Settings**
- User profile
- Notification preferences
- Privacy settings
- About the app
- Sign out

---

## Data Models (Frontend)

```dart
// User
class User {
  int id;
  String email;
  DateTime createdAt;
}

// Persona
class Persona {
  int id;
  String label;  // e.g., "React Developer"
  int weight;    // 1-10
  double? confidenceScore;  // 0-1
  DateTime createdAt;
}

// Interaction
class Interaction {
  int id;
  String mode;  // "live" or "recap"
  String transcriptExcerpt;
  List<Synapse> topSynapses;
  DateTime createdAt;
}

// Synapse (matched interest)
class Synapse {
  int personaId;
  String personaLabel;
  double similarity;  // 0-1
  int rank;  // 1-3
}

// Job (async operation status)
class Job {
  String id;
  String status;  // pending, processing, completed, failed
  int progress;  // 0-100
  String jobType;  // onboarding, interaction
  dynamic result;
  String? errorMessage;
}
```

---

## API Integration Points

### Authentication Endpoints
- `POST /auth/signup` - Create account
- `POST /auth/signin` - Sign in
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Sign out

### Onboarding Endpoints
- `POST /onboarding/voice-pitch` - Upload & process voice
- `POST /onboarding/linkedin-profile` - Process LinkedIn URL
- `GET /onboarding/persona` - Get all personas
- `PATCH /onboarding/persona/{id}` - Update persona
- `DELETE /onboarding/persona/{id}` - Delete persona

### Interaction Endpoints
- `POST /interactions/process-audio` - Process recorded interaction
- `GET /interactions/history` - Get past interactions
- `GET /interactions/{id}` - Get interaction details

### Feedback Endpoints
- `POST /feedback/persona/{id}` - Submit feedback on persona
- `GET /feedback/metrics` - Get performance metrics

### Job Status Endpoints
- `GET /jobs/status/{job_id}` - Poll job status
- `GET /jobs/list` - Get user's jobs
- `GET /jobs/` - Overview of jobs

---

## State Management Structure (Riverpod)

```dart
// Auth
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>
final userProvider = FutureProvider<User>

// Data
final personasProvider = FutureProvider<List<Persona>>
final interactionsProvider = FutureProvider<List<Interaction>>
final metricsProvider = FutureProvider<Metrics>

// Operations
final recordInteractionProvider = FutureProvider.family
final submitFeedbackProvider = FutureProvider.family
final uploadVoicePitchProvider = FutureProvider.family

// UI State
final selectedPersonaProvider = StateProvider<Persona?>
final recordingProvider = StateNotifierProvider<RecordingNotifier, RecordingState>
final jobStatusProvider = FutureProvider.family<Job, String>
```

---

## UI Flow Diagram

```
Splash Screen
    ↓
[Authenticated?]
    ├─→ NO: Auth Screen (Sign In/Up)
    │        ↓
    │   [User Created?]
    │        ├─→ YES: Onboarding Wizard
    │        │         ├─→ Choose Method (Voice/LinkedIn)
    │        │         ├─→ Process (uploads)
    │        │         ├─→ Review Personas
    │        │         └─→ Home Dashboard
    │        └─→ NO: Sign Up Form
    │
    └─→ YES: Home Dashboard
             ├─→ Record Interaction
             │   ├─→ Choose Mode (Live/Recap)
             │   ├─→ Record Audio
             │   ├─→ Show Results (Synapses)
             │   └─→ Back to Dashboard
             ├─→ Manage Personas
             │   ├─→ List Personas
             │   ├─→ Rate/Approve/Reject
             │   └─→ Back to Dashboard
             ├─→ View Metrics
             │   └─→ Analytics Dashboard
             └─→ Settings
                 └─→ Profile, Preferences, Sign Out
```

---

## Tech Stack Validation

✅ **State Management**: Riverpod (watch, read, provider families)
✅ **API Client**: Dio (interceptors for auth tokens)
✅ **Audio Recording**: record + just_audio packages
✅ **Local Storage**: Hive for offline personas/interactions
✅ **UI**: Flutter Material 3 (responsive)
✅ **Animations**: Lottie + Staggered animations for interactions
✅ **Forms**: Flutter Form Builder for setup wizard
✅ **Charts**: For metrics dashboard
✅ **Testing**: Mockito for API mocking

---

## Implementation Priority

**Phase 1 (MVP)**:
1. Auth screens (sign in/up)
2. Dashboard (basic)
3. Onboarding (voice + LinkedIn)
4. Personas management
5. API integration

**Phase 2**:
6. Audio recording
7. Interaction processing
8. Results display
9. Feedback submission

**Phase 3**:
10. Metrics dashboard
11. Advanced analytics
12. Notifications
13. Polish & animations
