import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

/// Firebase initialization and configuration
class FirebaseConfig {
  static Future<void> initialize() async {
    try {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    } catch (e) {
      throw Exception('Failed to initialize Firebase: $e');
    }
  }
}
