import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/entities/entities.dart';

enum OnboardingTourStep {
  entry,
  demoContact,
  searchRecall,
  insightShown,
  ownership,
  operational,
  signupGate,
  postSignup,
  habitBanner,
  complete,
}

class OnboardingTourState {
  final OnboardingTourStep step;
  final bool headlineVisible;
  final bool signupCompleted;

  OnboardingTourState({
    this.step = OnboardingTourStep.entry,
    this.headlineVisible = true,
    this.signupCompleted = false,
  });

  OnboardingTourState copyWith({
    OnboardingTourStep? step,
    bool? headlineVisible,
    bool? signupCompleted,
  }) {
    return OnboardingTourState(
      step: step ?? this.step,
      headlineVisible: headlineVisible ?? this.headlineVisible,
      signupCompleted: signupCompleted ?? this.signupCompleted,
    );
  }
}

class OnboardingTourNotifier extends StateNotifier<OnboardingTourState> {
  OnboardingTourNotifier(): super(OnboardingTourState());

  void dismissHeadline() {
    state = state.copyWith(headlineVisible: false, step: OnboardingTourStep.demoContact);
  }

  void goto(OnboardingTourStep step) {
    state = state.copyWith(step: step);
  }

  void completeSignup() {
    state = state.copyWith(signupCompleted: true, step: OnboardingTourStep.postSignup);
  }
}

final onboardingTourProvider = StateNotifierProvider<OnboardingTourNotifier, OnboardingTourState>(
  (ref) => OnboardingTourNotifier(),
);

/// Demo contacts that are used for the onboarding walkthrough. These are UI-only
/// until the user persists them via real save flow.
final demoContactsProvider = StateProvider<List<Persona>>((ref) => []);

final memoryIndexProvider = StateProvider<int>((ref) => 0);
