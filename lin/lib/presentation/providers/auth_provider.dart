/// Riverpod providers for authentication state management

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';
import '../../domain/entities/entities.dart';
import '../../data/datasources/remote/linkd_api_client.dart';

// ==================== DEPENDENCIES ====================

final dioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
  ));
});

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be initialized in main()');
});

final apiClientProvider = Provider<LinkdApiClient>((ref) {
  final dio = ref.watch(dioProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return LinkdApiClient(dio, prefs);
});

// ==================== AUTH STATE ====================

class AuthState {
  final User? user;
  final String? token;
  final bool isLoading;
  final String? error;
  final bool isAuthenticated;

  AuthState({
    this.user,
    this.token,
    this.isLoading = false,
    this.error,
    this.isAuthenticated = false,
  });

  AuthState copyWith({
    User? user,
    String? token,
    bool? isLoading,
    String? error,
    bool? isAuthenticated,
  }) {
    return AuthState(
      user: user ?? this.user,
      token: token ?? this.token,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final LinkdApiClient apiClient;
  final SharedPreferences prefs;

  AuthNotifier(this.apiClient, this.prefs)
      : super(
          AuthState(
            isAuthenticated: prefs.getBool('is_authenticated') ?? false,
            user: _loadUserFromPrefs(prefs),
            token: prefs.getString('auth_token'),
          ),
        );

  static User? _loadUserFromPrefs(SharedPreferences prefs) {
    final userJson = prefs.getString('user_json');
    if (userJson != null) {
      try {
        return User.fromJson(Map<String, dynamic>.from(
          Map<String, dynamic>.from({'': userJson}),
        ));
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  Future<void> signup({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await apiClient.signup(email: email, password: password);
      await prefs.setBool('is_authenticated', true);
      await prefs.setInt('user_id', response.user.id);
      state = state.copyWith(
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  Future<void> signin({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await apiClient.signin(email: email, password: password);
      await prefs.setBool('is_authenticated', true);
      await prefs.setInt('user_id', response.user.id);
      state = state.copyWith(
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  Future<void> demoSignin() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await apiClient.demoSignin();
      await prefs.setBool('is_authenticated', true);
      await prefs.setInt('user_id', response.user.id);
      state = state.copyWith(
        user: response.user,
        token: response.token,
        isLoading: false,
        isAuthenticated: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      await apiClient.logout();
      await prefs.remove('is_authenticated');
      await prefs.remove('user_id');
      await prefs.remove('auth_token');
      state = AuthState();
    } catch (e) {
      rethrow;
    }
  }

  void checkAuthStatus() {
    final isAuth = prefs.getBool('is_authenticated') ?? false;
    state = state.copyWith(isAuthenticated: isAuth);
  }
}

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return AuthNotifier(apiClient, prefs);
});

// Get current user
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.user;
});

// Check if user is authenticated
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.isAuthenticated;
});

// Get auth token
final authTokenProvider = Provider<String?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.token;
});
