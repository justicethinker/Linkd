import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/utils/service_locator.dart';
import 'core/utils/logger.dart';
import 'linkd_app.dart';
import 'presentation/providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
  try {
    await Firebase.initializeApp();
    AppLogger.info('Firebase initialized successfully');
  } catch (e) {
    AppLogger.error('Firebase initialization error', e);
  }

  // Setup service locator and dependencies
  await setupServiceLocator();

  // Initialize SharedPreferences for Riverpod
  final prefs = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const LinkdApp(),
    ),
  );
}
