import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:get_it/get_it.dart';

import '../constants/app_constants.dart';
import 'logger.dart';

/// Service locator / Dependency injection setup
final getIt = GetIt.instance;

Future<void> setupServiceLocator() async {
  // External dependencies
  final sharedPrefs = await SharedPreferences.getInstance();
  getIt.registerSingleton<SharedPreferences>(sharedPrefs);

  // HTTP Client
  final dio = Dio(BaseOptions(
    baseUrl: AppConstants.apiBaseUrl,
    connectTimeout: AppConstants.apiTimeout,
    receiveTimeout: AppConstants.apiTimeout,
  ));

  // Add interceptors
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        // Add auth token if available
        final token = sharedPrefs.getString(AppConstants.sessionTokenKey);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        AppLogger.debug('Request: ${options.method} ${options.path}');
        return handler.next(options);
      },
      onResponse: (response, handler) {
        AppLogger.debug('Response: ${response.statusCode} ${response.statusMessage}');
        return handler.next(response);
      },
      onError: (error, handler) {
        AppLogger.error('Error: ${error.message}');
        return handler.next(error);
      },
    ),
  );

  getIt.registerSingleton<Dio>(dio);

  AppLogger.info('Service locator initialized');
}
