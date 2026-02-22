import 'package:intl/intl.dart';

/// String extensions
extension StringExtensions on String {
  bool get isEmpty => trim().isEmpty;
  bool get isNotEmpty => !isEmpty;

  bool isValidEmail() {
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    );
    return emailRegex.hasMatch(this);
  }

  String capitalize() {
    if (isEmpty) return '';
    return this[0].toUpperCase() + substring(1);
  }

  String toTitleCase() {
    return split(' ')
        .map((word) => word.capitalize())
        .join(' ');
  }

  String truncate(int maxLength, {String ellipsis = '...'}) {
    if (length <= maxLength) return this;
    return substring(0, maxLength - ellipsis.length) + ellipsis;
  }
}

/// DateTime extensions
extension DateTimeExtensions on DateTime {
  String toFormattedString({String format = 'yyyy-MM-dd HH:mm'}) {
    return DateFormat(format).format(this);
  }

  String toReadableString() {
    final now = DateTime.now();
    final difference = now.difference(this);

    if (difference.inDays > 0) {
      return toFormattedString(format: 'MMM d, yyyy');
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'just now';
    }
  }

  bool isToday() {
    final today = DateTime.now();
    return year == today.year &&
        month == today.month &&
        day == today.day;
  }
}

/// Double extensions
extension DoubleExtensions on double {
  String toFormattedString({int decimalPlaces = 2}) {
    return toStringAsFixed(decimalPlaces);
  }

  String toPercentageString({int decimalPlaces = 1}) {
    return '${(this * 100).toStringAsFixed(decimalPlaces)}%';
  }
}

/// List extensions
extension ListExtensions<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
  T? get lastOrNull => isEmpty ? null : last;

  List<T> removeDuplicates() {
    return toSet().toList();
  }

  List<List<T>> chunk(int size) {
    if (isEmpty) return [];
    final chunks = <List<T>>[];
    for (int i = 0; i < length; i += size) {
      chunks.add(sublist(i, i + size > length ? length : i + size));
    }
    return chunks;
  }
}
