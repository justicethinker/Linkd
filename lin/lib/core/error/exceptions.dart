abstract class AppException implements Exception {
  final String message;

  AppException(this.message);

  @override
  String toString() => message;
}

class NetworkException extends AppException {
  NetworkException([String message = 'Network error occurred'])
      : super(message);
}

class ServerException extends AppException {
  final int? statusCode;

  ServerException(
    String message, {
    this.statusCode,
  }) : super(message);
}

class CacheException extends AppException {
  CacheException([String message = 'Cache error occurred'])
      : super(message);
}

class ValidationException extends AppException {
  ValidationException([String message = 'Validation error occurred'])
      : super(message);
}

class UnauthorizedException extends AppException {
  UnauthorizedException([String message = 'Unauthorized access'])
      : super(message);
}

class TimeoutException extends AppException {
  TimeoutException([String message = 'Request timeout'])
      : super(message);
}

class NotFoundException extends AppException {
  NotFoundException([String message = 'Resource not found'])
      : super(message);
}
