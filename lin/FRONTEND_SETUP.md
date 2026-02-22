# Linkd Flutter Frontend

Cross-platform mobile application for Linkd built with Flutter.

## 📱 Tech Stack

- **Framework**: Flutter 3.x
- **Language**: Dart 3.x
- **State Management**: Riverpod + Hooks
- **Backend Integration**: Dio HTTP Client
- **Firebase Services**: 
  - Firebase Auth
  - Cloud Firestore
  - Firebase Messaging (Push Notifications)
  - Firebase Analytics
  - Firebase Crashlytics
  - Firebase Storage
- **Local Storage**: Hive (NoSQL) + Shared Preferences
- **UI/UX**: 
  - Animated Text Kit
  - Lottie Animations
  - Flutter Staggered Animations
  - Flutter Spinkit (Loading indicators)
  - Confetti effects
- **Audio**: Record + Flutter Sound + Just Audio
- **Forms**: Flutter Form Builder
- **Network**: Dio with interceptors

## 🚀 Quick Start

### Prerequisites

- Flutter SDK 3.x ([Install Flutter](https://flutter.dev/docs/get-started/install))
- Dart SDK 3.x (comes with Flutter)
- Firebase Account
- Android Studio / Xcode (for native development)

### Installation

1. **Navigate to the project directory**
   ```bash
   cd linkd_app
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Configure Firebase**
   ```bash
   flutterfire configure
   ```
   This will generate `firebase_options.dart` with your Firebase project credentials.

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the app**
   ```bash
   flutter run
   ```

## 📁 Project Structure

```
lib/
├── core/
│   ├── constants/          # App-wide constants
│   ├── extensions/         # Dart/Flutter extensions
│   ├── theme/              # App theme configuration
│   ├── error/              # Custom exceptions
│   └── utils/              # Utilities (Firebase, Service Locator, Logger)
├── data/
│   ├── datasources/        # Remote & Local data sources
│   ├── models/             # Data models with serialization
│   └── repositories/       # Repository implementations
├── domain/
│   ├── entities/           # Business entities
│   ├── repositories/       # Repository interfaces
│   └── usecases/           # Business logic
├── presentation/
│   ├── pages/              # Full page screens
│   ├── widgets/            # Reusable widgets
│   └── providers/          # Riverpod providers
└── main.dart               # App entry point
```

## 🔧 Configuration

### Firebase Setup

1. **Create a Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Create a new project or select existing one
   - Enable required services (Auth, Firestore, Storage, etc.)

2. **Add Your App to Firebase**
   ```bash
   flutterfire configure
   ```

3. **Authentication Setup**
   - Enable Google Sign-In in Firebase Console
   - Enable Apple Sign-In (for iOS)
   - Enable Email/Password authentication

4. **Firestore Database**
   - Create Firestore database
   - Set security rules for development/production

5. **Cloud Storage**
   - Enable Cloud Storage
   - Configure CORS for web access

### API Configuration

Update `lib/core/constants/app_constants.dart` with your backend API URL:

```dart
static const String apiBaseUrl = 'https://your-api.linkd.app';
```

## 🎯 Key Features Setup

### State Management (Riverpod)

Create providers in `lib/presentation/providers/`:

```dart
final userProvider = FutureProvider<User>((ref) async {
  // Fetch user data
});
```

### Local Storage (Hive)

1. Generate Hive adapters:
   ```bash
   flutter pub run build_runner build
   ```

2. Use Hive for offline data:
   ```dart
   final box = await Hive.openBox('entities');
   ```

### Audio Recording

Use the `record` package:

```dart
final recorder = AudioRecorder();
if (await recorder.hasPermission()) {
  await recorder.start();
}
```

### Push Notifications (Firebase Messaging)

Configure in `lib/core/services/firebase_messaging_service.dart`:

```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  // Handle message
});
```

## 🧪 Testing

### Unit Tests

```bash
flutter test
```

### Integration Tests

```bash
flutter test integration_test
```

### Build APK (Android)

```bash
flutter build apk --release
```

### Build IPA (iOS)

```bash
flutter build ios --release
```

### Build Web

```bash
flutter build web --release
```

## 📊 Performance Optimization

1. **Image Caching**: Use `cached_network_image` for remote images
2. **LazyLoading**: Implement pagination for lists
3. **Code Splitting**: Use responsive layouts
4. **Sound Null Safety**: Entire codebase is null-safe

## 🔐 Security Best Practices

1. **API Keys**: Store in `.env` file and `.gitignore` it
2. **Firebase Rules**: Set restrictive Firestore rules
3. **Authentication**: Use Firebase Auth for secure token management
4. **Data Encryption**: Encrypt sensitive data in Hive

## 🐛 Debugging

### Enable Debug Logging

Set `DEBUG_MODE=true` in `.env`

### Use Flutter DevTools

```bash
flutter pub global activate devtools
devtools
```

### View Logs

```bash
flutter logs
```

## 📚 Documentation

- [Flutter Official Docs](https://flutter.dev/docs)
- [Dart Documentation](https://dart.dev/guides)
- [Riverpod Docs](https://riverpod.dev)
- [Firebase Flutter Setup](https://firebase.flutter.dev)
- [Hive Documentation](https://docs.hivedb.dev)

## 🤝 Contributing

1. Create a feature branch
2. Make changes following Dart style guidelines
3. Run tests and linting
4. Submit PR with description

## 📝 License

This project is part of the Linkd ecosystem.

## 🆘 Troubleshooting

### Firebase Configuration Issues

```bash
flutterfire configure --overwrite
```

### Dependency Issues

```bash
flutter clean
flutter pub get
```

### Build Issues

```bash
flutter clean
flutter pub cache repair
flutter pub get
flutter run
```

## 🚀 Next Steps

1. Update `firebase_options.dart` with your Firebase credentials
2. Configure API endpoints in `.env`
3. Implement authentication screens
4. Set up Firestore database schema
5. Implement core features (search, entities, connections)
