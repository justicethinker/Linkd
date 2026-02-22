import 'package:flutter/material.dart';

/// Application theme configuration

class AppTheme {
  static const Color primaryColor = Color(0xFF0066FF);
  static const Color secondaryColor = Color(0xFF00CC88);
  static const Color accentColor = Color(0xFFFF6B6B);
  
  static const Color backgroundColor = Color(0xFFF8F9FA);
  static const Color surfaceColor = Color(0xFFFFFFFF);
  static const Color errorColor = Color(0xFFEE5A52);
  
  static const Color textPrimary = Color(0xFF1A1A1A);
  static const Color textSecondary = Color(0xFF666666);
  static const Color textHint = Color(0xFFAAAAAA);
  
  static const Color borderColor = Color(0xFFE0E0E0);
  static const Color dividerColor = Color(0xFFF0F0F0);

  static ThemeData lightTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      primaryColor: primaryColor,
      scaffoldBackgroundColor: backgroundColor,
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceColor,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: true,
      ),
      colorScheme: ColorScheme.light(
        primary: primaryColor,
        secondary: secondaryColor,
        surface: surfaceColor,
        error: errorColor,
      ),
      textTheme: _buildTextTheme(),
      inputDecorationTheme: _buildInputDecorationTheme(),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
    );
  }

  static ThemeData darkTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      primaryColor: primaryColor,
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF1A1A1A),
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: secondaryColor,
        surface: Color(0xFF2A2A2A),
        error: errorColor,
      ),
      textTheme: _buildDarkTextTheme(),
      inputDecorationTheme: _buildDarkInputDecorationTheme(),
    );
  }

  static TextTheme _buildTextTheme() {
    return const TextTheme(
      displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: textPrimary),
      displayMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: textPrimary),
      displaySmall: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: textPrimary),
      headlineMedium: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: textPrimary),
      headlineSmall: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: textPrimary),
      titleLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: textPrimary),
      titleMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: textPrimary),
      titleSmall: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: textSecondary),
      bodyLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.normal, color: textPrimary),
      bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.normal, color: textPrimary),
      bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.normal, color: textSecondary),
      labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: primaryColor),
    );
  }

  static TextTheme _buildDarkTextTheme() {
    return const TextTheme(
      displayLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
      displayMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
      displaySmall: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
      headlineMedium: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white),
      headlineSmall: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white),
      titleLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
      titleMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Colors.white),
      titleSmall: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFFAAAAAA)),
      bodyLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.normal, color: Colors.white),
      bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.normal, color: Colors.white),
      bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.normal, color: Color(0xFFAAAAAA)),
      labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: primaryColor),
    );
  }

  static InputDecorationTheme _buildInputDecorationTheme() {
    return InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: borderColor),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: borderColor),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: primaryColor, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: errorColor),
      ),
      filled: true,
      fillColor: surfaceColor,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      hintStyle: const TextStyle(color: textHint, fontSize: 14),
    );
  }

  static InputDecorationTheme _buildDarkInputDecorationTheme() {
    return InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF444444)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF444444)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: primaryColor, width: 2),
      ),
      filled: true,
      fillColor: Color(0xFF2A2A2A),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      hintStyle: const TextStyle(color: Color(0xFF888888), fontSize: 14),
    );
  }
}
