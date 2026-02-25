import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/onboarding_tour_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/entities.dart';

class HeadlineOverlay extends ConsumerStatefulWidget {
  const HeadlineOverlay({super.key});

  @override
  ConsumerState<HeadlineOverlay> createState() => _HeadlineOverlayState();
}

class _HeadlineOverlayState extends ConsumerState<HeadlineOverlay> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 400));
    _ctrl.value = 1.0;
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _onTryDemo() async {
    await _ctrl.reverse();
    ref.read(onboardingTourProvider.notifier).dismissHeadline();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _ctrl,
      child: Container(
        color: AppTheme.surfaceColor.withOpacity(0.95),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Turn conversations into lasting advantages.',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'Never forget what matters about the people you meet.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppTheme.textSecondary),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ElevatedButton(
                      onPressed: _onTryDemo,
                      child: const Text('Try Interactive Demo'),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton(
                      onPressed: () => ref.read(onboardingTourProvider.notifier).goto(OnboardingTourStep.ownership),
                      child: const Text('Record someone I met'),
                    ),
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class DemoContactCard extends ConsumerStatefulWidget {
  const DemoContactCard({super.key});

  @override
  ConsumerState<DemoContactCard> createState() => _DemoContactCardState();
}

class _DemoContactCardState extends ConsumerState<DemoContactCard> {
  bool showLine1 = false;
  bool showLine2 = false;
  bool showLine3 = false;

  @override
  void initState() {
    super.initState();
    _performReveal();
  }

  void _performReveal() async {
    setState(() => showLine1 = true);
    await Future.delayed(const Duration(milliseconds: 250));
    setState(() => showLine2 = true);
    await Future.delayed(const Duration(milliseconds: 180));
    setState(() => showLine3 = true);
    // add to demo contacts provider if empty
    final list = ref.read(demoContactsProvider);
    if (list.isEmpty) {
      final demo = Persona(id: -1, label: 'Sarah Chen', weight: 5.0, confidenceScore: 0.9, createdAt: DateTime.now());
      ref.read(demoContactsProvider.notifier).state = [demo];
    }
  }

  @override
  Widget build(BuildContext context) {
    final persona = ref.watch(demoContactsProvider).firstOrNull;
    if (persona == null) return const SizedBox.shrink();

    return Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Material(
          elevation: 4,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(16),
            width: 360,
            decoration: BoxDecoration(
              color: AppTheme.surfaceColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AnimatedOpacity(
                  opacity: showLine1 ? 1 : 0,
                  duration: const Duration(milliseconds: 300),
                  child: Transform.translate(
                    offset: Offset(0, showLine1 ? 0 : 4),
                    child: Text('${persona.label} — Product Designer', style: Theme.of(context).textTheme.titleMedium),
                  ),
                ),
                const SizedBox(height: 8),
                AnimatedOpacity(
                  opacity: showLine2 ? 1 : 0,
                  duration: const Duration(milliseconds: 300),
                  child: Transform.translate(
                    offset: Offset(0, showLine2 ? 0 : 3),
                    child: Text('Company: Acme Studio', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.textSecondary)),
                  ),
                ),
                const SizedBox(height: 8),
                AnimatedOpacity(
                  opacity: showLine3 ? 1 : 0,
                  duration: const Duration(milliseconds: 300),
                  child: Transform.translate(
                    offset: Offset(0, showLine3 ? 0 : 2),
                    child: Text('Shared Interests Detected: AI, Startups', style: Theme.of(context).textTheme.bodyMedium),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class InsightPanel extends ConsumerWidget {
  final String title;
  final String subtitle;
  const InsightPanel({super.key, required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Align(
      alignment: Alignment.center,
      child: Padding(
        padding: const EdgeInsets.only(top: 220.0),
        child: Container(
          width: 360,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.surfaceColor,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8)],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.lightbulb, color: AppTheme.primaryColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(subtitle, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.textSecondary)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class RecordingModal {
  static Future<void> show(BuildContext context, WidgetRef ref) async {
    final nameController = TextEditingController();
    final noteController = TextEditingController();
    bool showOptional = false;

    await showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Record someone you met'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(hintText: 'Name (required)'),
              ),
              const SizedBox(height: 12),
              if (showOptional) ...[
                TextField(
                  controller: noteController,
                  decoration: const InputDecoration(hintText: 'One sentence memory note (required)'),
                ),
                const SizedBox(height: 12),
                TextField(
                  decoration: const InputDecoration(hintText: 'Tag / Context (optional)'),
                ),
              ] else ...[
                TextButton(
                  onPressed: () => setState(() => showOptional = true),
                  child: const Text('Add memory note'),
                ),
              ]
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () {
                // Simple validation
                if (nameController.text.trim().isEmpty) return;
                if (showOptional && noteController.text.trim().isEmpty) return;

                // Add to demo contacts and increment memory index
                final demo = Persona(id: -2, label: nameController.text.trim(), weight: 5, confidenceScore: 0.9, createdAt: DateTime.now());
                final list = ref.read(demoContactsProvider);
                ref.read(demoContactsProvider.notifier).state = [...list, demo];
                ref.read(memoryIndexProvider.notifier).state = ref.read(memoryIndexProvider) + 1;

                Navigator.pop(context);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}

class SignupGateOverlay extends ConsumerWidget {
  const SignupGateOverlay({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: Container(
        width: 520,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Save your memory system and your first connection.', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ElevatedButton(onPressed: () { ref.read(onboardingTourProvider.notifier).completeSignup(); }, child: const Text('Continue with Google')),
                const SizedBox(width: 12),
                ElevatedButton(onPressed: () { ref.read(onboardingTourProvider.notifier).completeSignup(); }, child: const Text('Continue with LinkedIn')),
              ],
            ),
            const SizedBox(height: 12),
            Text('Don\'t risk losing what you\'ve just built.', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.textSecondary)),
          ],
        ),
      ),
    );
  }
}

// Helper extension
extension FirstOrNull<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : this[0];
}
