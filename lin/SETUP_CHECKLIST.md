# Flutter Frontend Setup Checklist

## ✅ Completed

- [x] Flutter SDK installed and configured
- [x] Flutter project created (`linkd_app`)
- [x] All dependencies added to `pubspec.yaml`
- [x] Project structure set up (Clean Architecture + Riverpod)
- [x] Theme configuration created
- [x] Constants and utilities set up
- [x] Service locator (GetIt) configured
- [x] Logger utility implemented
- [x] Extensions for common types created
- [x] Home page with sample UI created
- [x] Main app entry point configured with Riverpod
- [x] Environment configuration files created

## 🔧 Next Steps - Firebase Configuration

### 1. Create Firebase Project (if not already done)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or select existing one
3. Name it: `linkd` (or your preference)
4. Enable/accept Google Analytics (recommended)

### 2. Set Up FlutterFire

```bash
cd linkd_app
flutterfire configure
```

This command will:
- Detect your platforms (Android, iOS, Web)
- Generate `firebase_options.dart` with credentials
- Update Android and iOS native configurations

### 3. Firebase Services to Enable

In Firebase Console, enable these services:

#### Authentication
- Go to Authentication section
- Enable sign-in methods:
  - [ ] Email/Password
  - [ ] Google Sign-In
  - [ ] Apple Sign-In (for iOS)
  - [ ] LinkedIn (custom provider or OAuth)

#### Firestore Database
1. Go to Firestore Database
2. Create database
3. Start in test mode (then update rules for production)
4. Define collections:
   - `users` - User profiles
   - `entities` - LinkedIn entities (profiles, companies)
   - `connections` - User connections/relationships
   - `conversations` - Chat/interaction history
   - `feedback` - User feedback/ratings

#### Cloud Storage
1. Go to Storage section
2. Create bucket
3. Update CORS configuration for web access
4. Use for: profile photos, entity images

#### Cloud Messaging (for push notifications)
1. Enable Firebase Messaging
2. Add server key from Project Settings
3. Integrate with backend for sending notifications

#### Analytics (optional)
1. Enable Google Analytics
2. Track user events (onboarding, searches, etc.)

#### Crashlytics (optional)
1. Enable Crashlytics
2. Auto-collects crash reports

### 4. Update Environment Configuration

Edit `linkd_app/.env` with your Firebase details:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_WEB_API_KEY=your-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
```

### 5. Test Installation

```bash
cd linkd_app
flutter pub get
flutter run
```

You should see the Linkd home page with "Welcome to Linkd" message.

## 🏗️ Architecture Overview

### Clean Architecture Layers

```
Domain Layer (Business Logic)
    ├── entities/         - Pure business objects
    ├── repositories/     - Abstract repository interfaces
    └── usecases/         - Business logic operations

Data Layer (Data Management)
    ├── datasources/
    │   ├── local/        - Hive, SharedPreferences
    │   └── remote/       - API, Firebase calls
    ├── models/           - Data models with serialization
    └── repositories/     - Repository implementations

Presentation Layer (UI)
    ├── pages/            - Full screens
    ├── widgets/          - Reusable components
    └── providers/        - Riverpod state management
```

### State Management with Riverpod

Create providers for different concerns:

```dart
// Simple state
final userNameProvider = StateProvider<String>((ref) => '');

// Async data fetching
final userDataProvider = FutureProvider<User>((ref) async {
  return await userRepository.getUser();
});

// Computed/derived state
final isUserLoggedInProvider = Provider<bool>((ref) {
  return ref.watch(userDataProvider).maybeWhen(
    data: (user) => user != null,
    orElse: () => false,
  );
});

// Async operations
final fetchUserProvider = FutureProvider.family<User, String>((ref, userId) async {
  return await userRepository.getUserById(userId);
});
```

## 📱 Key Screens to Implement

1. **Splash/Loading Screen**
   - Show app logo with Lottie animation
   - Check authentication status

2. **Authentication Screens**
   - Sign in
   - Sign up
   - Forgot password
   - Social auth (Google, Apple, LinkedIn)

3. **Onboarding Screens**
   - Welcome flow
   - Personalization settings
   - Permission requests

4. **Home/Dashboard**
   - Entity search
   - Recent entities
   - Connections overview
   - Quick actions

5. **Entity Detail Screen**
   - Profile information
   - Connection status
   - Action buttons (Connect, Save, Share)

6. **Search/Filters Screen**
   - Advanced search
   - Filters (industry, location, skills)
   - Saved searches

7. **Connections Screen**
   - List of connections
   - Connection insights
   - Batch operations

8. **Audio Recording Screen**
   - Record voice notes
   - Playback
   - Sharing options

9. **Settings Screen**
   - Profile management
   - Preferences
   - About & Help

## 📦 Key Packages Usage

### Riverpod
```dart
final counterProvider = StateProvider<int>((ref) => 0);

// In widget:
final count = ref.watch(counterProvider);
ref.read(counterProvider.notifier).state++;
```

### Dio HTTP Client
```dart
final dio = getIt<Dio>();
final response = await dio.get('/api/users');
```

### Hive Local Storage
```dart
final box = await Hive.openBox('myBox');
await box.put('key', value);
final data = box.get('key');
```

### Firebase Auth
```dart
final auth = FirebaseAuth.instance;
final user = await auth.signInWithEmailAndPassword(
  email: email,
  password: password,
);
```

### Lottie Animations
```dart
Lottie.asset('assets/animations/success.json')
```

### Audio Recording
```dart
final recorder = AudioRecorder();
await recorder.start();
```

## 🧪 Testing Setup

### Unit Tests
```bash
flutter test
```

### Widget Tests
```dart
testWidgets('Widget test', (WidgetTester tester) async {
  await tester.pumpWidget(const MyApp());
  expect(find.text('Linkd'), findsOneWidget);
});
```

### Integration Tests
```bash
flutter test integration_test
```

## 📊 Performance Tips

1. **Image Optimization**
   - Use `cached_network_image` for remote images
   - Compress local images
   - Use appropriate image sizes

2. **List Performance**
   - Use `ListView.builder` for large lists
   - Implement pagination
   - Cache list items

3. **State Management**
   - Keep providers focused and simple
   - Use `.select()` to watch specific fields
   - Avoid rebuilds with proper invalidation

4. **Build Performance**
   - Use `const` constructors
   - Avoid rebuilding entire screens
   - Profile with DevTools

## 🔐 Security Checklist

- [ ] Never commit `.env` file
- [ ] Use environment-specific Firebase configs
- [ ] Implement token refresh for API calls
- [ ] Validate user input
- [ ] Use HTTPS for all API calls
- [ ] Encrypt sensitive data in Hive
- [ ] Set up proper Firestore security rules
- [ ] Review Firebase authentication methods

## 🚀 Building for Release

### Android
```bash
flutter build apk --release
flutter build appbundle --release
```

### iOS
```bash
flutter build ios --release
```

### Web
```bash
flutter build web --release
```

## 📚 Documentation Links

- [Flutter Docs](https://flutter.dev)
- [Riverpod Getting Started](https://riverpod.dev/docs/getting_started)
- [Firebase Flutter](https://firebase.flutter.dev)
- [Hive Database](https://docs.hivedb.dev)
- [Dio HTTP Client](https://pub.dev/packages/dio)

## 🆘 Common Issues & Solutions

### Firebase Not Initializing
```bash
flutterfire configure --overwrite
flutter clean
flutter pub get
```

### Build Errors
```bash
flutter clean
flutter pub cache repair
flutter pub get
flutter run
```

### Hot Reload Not Working
- Try hot restart: `r` in terminal
- Or run: `flutter run` again

### Android Build Issues
- Check `android/gradle.properties`
- Ensure Java/Gradle compatibility
- Update Android SDK

## ✨ Next Major Tasks

1. Implement Firebase Authentication flow
2. Create user profile management
3. Set up Firestore data models
4. Implement search functionality
5. Build entity detail screens
6. Add audio recording features
7. Integrate with backend API
8. Implement push notifications
9. Add offline support with Hive
10. Set up analytics and crash reporting

---

**Questions?** Check [FRONTEND_SETUP.md](./FRONTEND_SETUP.md) for detailed documentation.
