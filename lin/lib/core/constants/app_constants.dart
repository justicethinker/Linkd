class AppConstants {
  // API Configuration
  static const String apiBaseUrl = 'http://localhost:8000';
  static const Duration apiTimeout = Duration(seconds: 30);

  // Firebase Configuration
  static const String firebaseProjectId = 'linkd-project';
  static const String firebaseAppId = 'your-firebase-app-id';
  static const String firebaseSenderId = 'your-sender-id';

  // Storage Keys
  static const String sessionTokenKey = 'session_token';
  static const String userPreferencesKey = 'user_preferences';
  static const String onboardingCompletedKey = 'onboarding_completed';

  // App Info
  static const String appName = 'Linkd';
  static const String appVersion = '1.0.0';

  // Error Messages
  static const String networkError = 'Network error. Please check your connection.';
  static const String serverError = 'Server error. Please try again later.';
  static const String unknownError = 'An unknown error occurred.';
  static const String timeoutError = 'Request timeout. Please try again.';

  // Pagination
  static const int pageSize = 20;
  static const int initialPage = 1;

  // Delays
  static const Duration animationDuration = Duration(milliseconds: 300);
  static const Duration debounceDelay = Duration(milliseconds: 500);
}
