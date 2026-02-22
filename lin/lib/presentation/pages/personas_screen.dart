import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/app_providers.dart';


/// Personas management screen
class PersonasScreen extends ConsumerWidget {
  const PersonasScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final personasAsync = ref.watch(personasProvider);
    final selectedPersona = ref.watch(selectedPersonaProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Your Personas'),
      ),
      body: personasAsync.when(
        data: (personas) {
          if (personas.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.person_outline,
                    size: 80,
                    color: AppTheme.textSecondary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No personas yet',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Create your first persona from voice pitch or LinkedIn',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            );
          }

          return ListView.builder(
            itemCount: personas.length,
            padding: const EdgeInsets.all(16),
            itemBuilder: (context, index) {
              final persona = personas[index];
              return PersonaCard(
                persona: persona,
                isSelected: selectedPersona?.id == persona.id,
                onTap: () {
                  ref.read(selectedPersonaProvider.notifier).state = persona;
                },
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error: $err')),
      ),
    );
  }
}

class PersonaCard extends ConsumerWidget {
  final persona;
  final bool isSelected;
  final VoidCallback onTap;

  const PersonaCard({
    super.key,
    required this.persona,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        color: isSelected
            ? AppTheme.primaryColor.withValues(alpha: 0.1)
            : AppTheme.surfaceColor,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: AppTheme.primaryColor.withValues(alpha: 0.2),
                    radius: 24,
                    child: Text(
                      persona.label[0].toUpperCase(),
                      style: const TextStyle(
                        color: AppTheme.primaryColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 20,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          persona.label,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Weight: ${persona.weight}/10',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  PopupMenuButton<String>(
                    itemBuilder: (context) => [
                      const PopupMenuItem<String>(
                        value: 'approve',
                        child: Text('Approve'),
                      ),
                      const PopupMenuItem<String>(
                        value: 'reject',
                        child: Text('Reject'),
                      ),
                      const PopupMenuItem<String>(
                        value: 'rate',
                        child: Text('Rate'),
                      ),
                      const PopupMenuDivider(),
                      const PopupMenuItem<String>(
                        value: 'delete',
                        child: Text('Delete'),
                      ),
                    ],
                    onSelected: (value) {
                      _handlePersonaAction(
                        context,
                        ref,
                        value,
                        persona.id,
                      );
                    },
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Weight indicator
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Weight',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: persona.weight / 10,
                      minHeight: 8,
                      backgroundColor: AppTheme.borderColor,
                      valueColor: AlwaysStoppedAnimation(
                        _getWeightColor(persona.weight),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handlePersonaAction(
    BuildContext context,
    WidgetRef ref,
    String action,
    int personaId,
  ) {
    if (action.contains('Approve')) {
      ref.read(submitFeedbackProvider(
        (
          personaId: personaId,
          feedbackType: 'approved',
          rating: null,
          notes: null,
        ),
      ));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Persona approved!')),
      );
    } else if (action.contains('Reject')) {
      ref.read(submitFeedbackProvider(
        (
          personaId: personaId,
          feedbackType: 'rejected',
          rating: null,
          notes: null,
        ),
      ));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Persona rejected!')),
      );
    } else if (action.contains('Delete')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Delete functionality - coming soon')),
      );
    }
  }

  Color _getWeightColor(int weight) {
    if (weight <= 3) return Colors.red;
    if (weight <= 6) return Colors.orange;
    if (weight <= 8) return Colors.blue;
    return AppTheme.secondaryColor;
  }
}
