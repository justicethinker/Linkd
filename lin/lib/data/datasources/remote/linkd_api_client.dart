/// Linkd API Client - handles all HTTP requests to backend

import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../domain/entities/entities.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/utils/logger.dart';

class LinkdApiClient {
  late Dio _dio;
  late SharedPreferences _prefs;

  LinkdApiClient(this._dio, this._prefs) {
    _setupInterceptors();
  }

  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // Add auth token
          final token = _prefs.getString('auth_token');
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          options.headers['Content-Type'] = 'application/json';
          AppLogger.debug('API Request: ${options.method} ${options.path}');
          return handler.next(options);
        },
        onResponse: (response, handler) {
          AppLogger.debug('API Response: ${response.statusCode} ${response.requestOptions.path}');
          return handler.next(response);
        },
        onError: (error, handler) {
          AppLogger.error('API Error: ${error.message}');
          return handler.next(error);
        },
      ),
    );
  }

  // ==================== AUTH ENDPOINTS ====================

  Future<AuthResponse> signup({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/auth/signup',
        data: {
          'email': email,
          'password': password,
        },
      );
      final authResponse = AuthResponse.fromJson(response.data);
      await _prefs.setString('auth_token', authResponse.token);
      return authResponse;
    } catch (e) {
      rethrow;
    }
  }

  Future<AuthResponse> signin({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/auth/signin',
        data: {
          'email': email,
          'password': password,
        },
      );
      final authResponse = AuthResponse.fromJson(response.data);
      await _prefs.setString('auth_token', authResponse.token);
      return authResponse;
    } catch (e) {
      rethrow;
    }
  }

  Future<AuthResponse> demoSignin() async {
    try {
      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/auth/demo-signin',
      );
      final authResponse = AuthResponse.fromJson(response.data);
      await _prefs.setString('auth_token', authResponse.token);
      return authResponse;
    } catch (e) {
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      await _prefs.remove('auth_token');
      await _prefs.remove('user_id');
    } catch (e) {
      rethrow;
    }
  }

  // ==================== ONBOARDING ENDPOINTS ====================

  Future<Map<String, dynamic>> uploadVoicePitch({
    required int userId,
    required String filePath,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'user_id': userId,
        'file': await MultipartFile.fromFile(filePath),
      });

      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/onboarding/voice-pitch',
        data: formData,
      );
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  Future<Map<String, dynamic>> uploadLinkedInProfile({
    required int userId,
    required String profileUrl,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'user_id': userId,
        'profile_url': profileUrl,
      });

      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/onboarding/linkedin-profile',
        data: formData,
      );
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  // ==================== PERSONAS ENDPOINTS ====================

  Future<List<Persona>> getPersonas(int userId) async {
    try {
      final response = await _dio.get(
        '${AppConstants.apiBaseUrl}/onboarding/persona',
        queryParameters: {'user_id': userId},
      );
      final personas = (response.data as List)
          .map((p) => Persona.fromJson(p))
          .toList();
      return personas;
    } catch (e) {
      rethrow;
    }
  }

  Future<Persona> getPersona(int userId, int personaId) async {
    try {
      final response = await _dio.get(
        '${AppConstants.apiBaseUrl}/onboarding/persona/$personaId',
        queryParameters: {'user_id': userId},
      );
      return Persona.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<Persona> updatePersona({
    required int userId,
    required int personaId,
    String? label,
    int? weight,
  }) async {
    try {
      final response = await _dio.patch(
        '${AppConstants.apiBaseUrl}/onboarding/persona/$personaId',
        queryParameters: {'user_id': userId},
        data: {
          if (label != null) 'label': label,
          if (weight != null) 'weight': weight,
        },
      );
      return Persona.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> deletePersona(int userId, int personaId) async {
    try {
      await _dio.delete(
        '${AppConstants.apiBaseUrl}/onboarding/persona/$personaId',
        queryParameters: {'user_id': userId},
      );
    } catch (e) {
      rethrow;
    }
  }

  // ==================== INTERACTION ENDPOINTS ====================

  Future<Map<String, dynamic>> processInteractionAudio({
    required int userId,
    required String filePath,
    required String mode, // "live" or "recap"
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'user_id': userId,
        'file': await MultipartFile.fromFile(filePath),
        'mode': mode,
      });

      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/interactions/process-audio',
        data: formData,
      );
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  // ==================== FEEDBACK ENDPOINTS ====================

  Future<Map<String, dynamic>> submitPersonaFeedback({
    required int userId,
    required int personaId,
    required String feedbackType, // "approved", "rejected", "rated"
    int? rating,
    String? notes,
  }) async {
    try {
      final response = await _dio.post(
        '${AppConstants.apiBaseUrl}/feedback/persona/$personaId',
        queryParameters: {'user_id': userId},
        data: {
          'feedback_type': feedbackType,
          if (rating != null) 'rating': rating,
          if (notes != null) 'notes': notes,
        },
      );
      return response.data;
    } catch (e) {
      rethrow;
    }
  }

  Future<Metrics> getMetrics(int userId) async {
    try {
      final response = await _dio.get(
        '${AppConstants.apiBaseUrl}/feedback/metrics',
        queryParameters: {'user_id': userId},
      );
      return Metrics.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  // ==================== JOB STATUS ENDPOINTS ====================

  Future<Job> getJobStatus(int userId, String jobId) async {
    try {
      final response = await _dio.get(
        '${AppConstants.apiBaseUrl}/jobs/status/$jobId',
        queryParameters: {'user_id': userId},
      );
      return Job.fromJson(response.data);
    } catch (e) {
      rethrow;
    }
  }

  Future<List<Job>> getJobsList(
    int userId, {
    String? status,
    int limit = 50,
  }) async {
    try {
      final response = await _dio.get(
        '${AppConstants.apiBaseUrl}/jobs/list',
        queryParameters: {
          'user_id': userId,
          if (status != null) 'status': status,
          'limit': limit,
        },
      );
      final jobs = (response.data['jobs'] as List)
          .map((j) => Job.fromJson(j))
          .toList();
      return jobs;
    } catch (e) {
      rethrow;
    }
  }
}
