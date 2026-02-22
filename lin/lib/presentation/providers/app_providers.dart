/// Riverpod providers for app data and operations

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/entities/entities.dart';
import 'auth_provider.dart';

// ==================== DATA PROVIDERS ====================

/// Get all personas for current user
final personasProvider = FutureProvider.autoDispose<List<Persona>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) return [];
  return apiClient.getPersonas(user.id);
});

/// Get single persona
final personaProvider = FutureProvider.autoDispose.family<Persona, int>((ref, personaId) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  return apiClient.getPersona(user.id, personaId);
});

/// Get metrics
final metricsProvider = FutureProvider.autoDispose<Metrics>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) {
    return Metrics(
      totalInteractions: 0,
      avgExtractionAccuracy: 0,
      approvalRate: 0,
      avgProcessingTimeMs: 0,
      avgTopSimilarity: 0,
      totalApproved: 0,
      totalRejected: 0,
    );
  }
  return apiClient.getMetrics(user.id);
});

/// Get job status
final jobStatusProvider = FutureProvider.autoDispose.family<Job, String>((ref, jobId) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  return apiClient.getJobStatus(user.id, jobId);
});

// ==================== OPERATION PROVIDERS ====================

/// Upload voice pitch
final uploadVoicePitchProvider = FutureProvider.autoDispose.family<
    Map<String, dynamic>,
    String>((ref, filePath) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  
  final result = await apiClient.uploadVoicePitch(
    userId: user.id,
    filePath: filePath,
  );
  
  // Invalidate personas to refetch
  ref.invalidate(personasProvider);
  
  return result;
});

/// Upload LinkedIn profile
final uploadLinkedInProfileProvider = FutureProvider.autoDispose.family<
    Map<String, dynamic>,
    String>((ref, profileUrl) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  
  final result = await apiClient.uploadLinkedInProfile(
    userId: user.id,
    profileUrl: profileUrl,
  );
  
  // Invalidate personas to refetch
  ref.invalidate(personasProvider);
  
  return result;
});

/// Process interaction audio
final processInteractionAudioProvider = FutureProvider.autoDispose.family<
    Map<String, dynamic>,
    ({String filePath, String mode})>((ref, params) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  
  final result = await apiClient.processInteractionAudio(
    userId: user.id,
    filePath: params.filePath,
    mode: params.mode,
  );
  
  return result;
});

/// Submit persona feedback
final submitFeedbackProvider = FutureProvider.autoDispose.family<
    Map<String, dynamic>,
    ({
      int personaId,
      String feedbackType,
      int? rating,
      String? notes
    })>((ref, params) async {
  final apiClient = ref.watch(apiClientProvider);
  final user = ref.watch(currentUserProvider);
  if (user == null) throw Exception('User not authenticated');
  
  final result = await apiClient.submitPersonaFeedback(
    userId: user.id,
    personaId: params.personaId,
    feedbackType: params.feedbackType,
    rating: params.rating,
    notes: params.notes,
  );
  
  // Invalidate personas and metrics to refetch
  ref.invalidate(personasProvider);
  ref.invalidate(metricsProvider);
  
  return result;
});

// ==================== UI STATE ====================

/// Selected persona for viewing details
final selectedPersonaProvider = StateProvider<Persona?>((ref) => null);

/// Recording state (for audio recording)
enum RecordingMode { live, recap }

class RecordingState {
  final bool isRecording;
  final bool isProcessing;
  final Duration duration;
  final RecordingMode mode;
  final String? filePath;

  RecordingState({
    this.isRecording = false,
    this.isProcessing = false,
    this.duration = Duration.zero,
    this.mode = RecordingMode.recap,
    this.filePath,
  });

  RecordingState copyWith({
    bool? isRecording,
    bool? isProcessing,
    Duration? duration,
    RecordingMode? mode,
    String? filePath,
  }) {
    return RecordingState(
      isRecording: isRecording ?? this.isRecording,
      isProcessing: isProcessing ?? this.isProcessing,
      duration: duration ?? this.duration,
      mode: mode ?? this.mode,
      filePath: filePath ?? this.filePath,
    );
  }
}

final recordingStateProvider = StateProvider<RecordingState>((ref) => RecordingState());

/// Onboarding step tracker
enum OnboardingStep { chooseMethod, processing, confirmPersonas, complete }

class OnboardingState {
  final OnboardingStep step;
  final bool isProcessing;
  final int progress; // 0-100
  final List<Persona>? generatedPersonas;
  final String? error;

  OnboardingState({
    this.step = OnboardingStep.chooseMethod,
    this.isProcessing = false,
    this.progress = 0,
    this.generatedPersonas,
    this.error,
  });

  OnboardingState copyWith({
    OnboardingStep? step,
    bool? isProcessing,
    int? progress,
    List<Persona>? generatedPersonas,
    String? error,
  }) {
    return OnboardingState(
      step: step ?? this.step,
      isProcessing: isProcessing ?? this.isProcessing,
      progress: progress ?? this.progress,
      generatedPersonas: generatedPersonas ?? this.generatedPersonas,
      error: error ?? this.error,
    );
  }
}

final onboardingStateProvider = StateProvider<OnboardingState>((ref) => OnboardingState());
