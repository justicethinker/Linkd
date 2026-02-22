import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'presentation/pages/auth_screen.dart';
import 'presentation/pages/onboarding_screen.dart';
import 'presentation/providers/app_providers.dart';
import 'presentation/providers/auth_provider.dart';
import 'presentation/navigation/main_navigation.dart';

/// Root app widget that handles routing between auth and main screens
class LinkdApp extends ConsumerWidget {
  const LinkdApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final personasAsync = ref.watch(personasProvider);

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Linkd',
      theme: AppTheme.lightTheme(),
      darkTheme: AppTheme.darkTheme(),
      themeMode: ThemeMode.system,
      home: _buildHome(authState, personasAsync),
    );
  }

  Widget _buildHome(AuthState authState, AsyncValue<List> personasAsync) {
    if (authState.isAuthenticated) {
      // Check if user has personas
      return personasAsync.when(
        loading: () => const Scaffold(
          body: Center(
            child: CircularProgressIndicator(),
          ),
        ),
        error: (error, stack) => const MainNavigationShell(),
        data: (personas) {
          // If no personas, show onboarding
          if (personas.isEmpty) {
            return const OnboardingScreen();
          }
          // Otherwise show main navigation
          return const MainNavigationShell();
        },
      );
    } else {
      // Not authenticated, show auth screen
      return const AuthScreen();
    }
  }
}
