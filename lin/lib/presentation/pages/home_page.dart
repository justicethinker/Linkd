import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/auth_provider.dart';
import '../../presentation/providers/app_providers.dart';

/// Dashboard/Home screen - main hub for the app
class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final personasAsync = ref.watch(personasProvider);
    final metricsAsync = ref.watch(metricsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Linkd'),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              // Navigate to settings
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Welcome section
              if (user != null) ...[
                Text(
                  'Welcome back, ${user.email.split('@')[0]}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 24),
              ],

              // Quick stats
              personasAsync.when(
                data: (personas) => metricsAsync.when(
                  data: (metrics) => _buildStatsSection(context, personas, metrics),
                  loading: () => const CircularProgressIndicator(),
                  error: (err, _) => Text('Error: $err'),
                ),
                loading: () => const CircularProgressIndicator(),
                error: (err, _) => Text('Error: $err'),
              ),

              const SizedBox(height: 32),

              // Quick action buttons
              Text(
                'Quick Actions',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _buildActionCard(
                    context,
                    icon: Icons.mic,
                    title: 'Record\nInteraction',
                    onTap: () {
                      // Navigate to recording screen
                    },
                  ),
                  _buildActionCard(
                    context,
                    icon: Icons.person,
                    title: 'Manage\nPersonas',
                    onTap: () {
                      // Navigate to personas screen
                    },
                  ),
                  _buildActionCard(
                    context,
                    icon: Icons.bar_chart,
                    title: 'View\nMetrics',
                    onTap: () {
                      // Navigate to metrics screen
                    },
                  ),
                  _buildActionCard(
                    context,
                    icon: Icons.add_circle,
                    title: 'Add More\nPersonas',
                    onTap: () {
                      // Navigate to onboarding
                    },
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // Recent personas preview
              personasAsync.when(
                data: (personas) {
                  if (personas.isEmpty) {
                    return Column(
                      children: [
                        Text(
                          'No personas yet',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Start by creating personas from your voice pitch or LinkedIn profile',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ],
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Your Personas',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      ListView.builder(
                        itemCount: personas.take(3).length,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemBuilder: (context, index) {
                          final persona = personas[index];
                          return Card(
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: AppTheme.primaryColor.withValues(alpha: 0.2),
                                child: Text(
                                  persona.label[0].toUpperCase(),
                                  style: const TextStyle(
                                    color: AppTheme.primaryColor,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              title: Text(persona.label),
                              subtitle: Text('Weight: ${persona.weight}/10'),
                              trailing: Icon(
                                Icons.trending_up,
                                color: AppTheme.secondaryColor,
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                  );
                },
                loading: () => const CircularProgressIndicator(),
                error: (err, _) => Text('Error: $err'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatsSection(BuildContext context, List personas, metrics) {
    return Column(
      children: [
        Row(
          children: [
            _buildStatCard(
              context,
              title: 'Personas',
              value: personas.length.toString(),
              icon: Icons.person,
            ),
            const SizedBox(width: 12),
            _buildStatCard(
              context,
              title: 'Interactions',
              value: metrics.totalInteractions.toString(),
              icon: Icons.chat,
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            _buildStatCard(
              context,
              title: 'Accuracy',
              value: '${(metrics.avgExtractionAccuracy * 100).toStringAsFixed(0)}%',
              icon: Icons.check_circle,
            ),
            const SizedBox(width: 12),
            _buildStatCard(
              context,
              title: 'Approval Rate',
              value: '${(metrics.approvalRate * 100).toStringAsFixed(0)}%',
              icon: Icons.thumb_up,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStatCard(BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppTheme.borderColor,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: AppTheme.primaryColor, size: 28),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: AppTheme.primaryColor,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard(BuildContext context, {
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        decoration: BoxDecoration(
          color: AppTheme.surfaceColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppTheme.borderColor,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 40,
              color: AppTheme.primaryColor,
            ),
            const SizedBox(height: 12),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
