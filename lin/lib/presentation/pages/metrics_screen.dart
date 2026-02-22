import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/app_providers.dart';

/// Screen displaying user metrics and analytics
class MetricsScreen extends ConsumerWidget {
  const MetricsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final metricsAsync = ref.watch(metricsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Performance Metrics'),
      ),
      body: metricsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline,
                size: 48,
                color: Theme.of(context).colorScheme.error,
              ),
              const SizedBox(height: 16),
              Text('Error loading metrics: $error'),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => ref.refresh(metricsProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (metrics) => SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Summary Cards
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  children: [
                    _buildMetricCard(
                      context,
                      title: 'Total Interactions',
                      value: metrics.totalInteractions.toString(),
                      icon: Icons.comment,
                      color: AppTheme.primaryColor,
                    ),
                    _buildMetricCard(
                      context,
                      title: 'Total Personas',
                      value: metrics.totalPersonas.toString(),
                      icon: Icons.people,
                      color: AppTheme.secondaryColor,
                    ),
                    _buildMetricCard(
                      context,
                      title: 'Extraction Accuracy',
                      value:
                          '${(metrics.avgExtractionAccuracy * 100).toStringAsFixed(1)}%',
                      icon: Icons.show_chart,
                      color: Colors.green,
                    ),
                    _buildMetricCard(
                      context,
                      title: 'Approval Rate',
                      value: '${(metrics.approvalRate * 100).toStringAsFixed(1)}%',
                      icon: Icons.thumb_up,
                      color: Colors.orange,
                    ),
                  ],
                ),
                const SizedBox(height: 32),
                // Detailed Section
                Text(
                  'Detailed Analytics',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 16),
                _buildDetailCard(
                  context,
                  title: 'Top Performing Persona',
                  value: metrics.topPersona ?? 'N/A',
                  subtitle: 'Appears most frequently in interactions',
                  icon: Icons.star,
                ),
                const SizedBox(height: 12),
                _buildDetailCard(
                  context,
                  title: 'Average Interaction Length',
                  value:
                      '${(metrics.avgInteractionLength ?? 0).toStringAsFixed(1)}s',
                  subtitle: 'Average duration per recorded interaction',
                  icon: Icons.schedule,
                ),
                const SizedBox(height: 12),
                _buildDetailCard(
                  context,
                  title: 'Last Active',
                  value: _formatDate(metrics.lastInteractionAt),
                  subtitle: 'Time of most recent interaction',
                  icon: Icons.access_time,
                ),
                const SizedBox(height: 32),
                // Insights Section
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.lightbulb,
                              color: Colors.amber,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Insights',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        _buildInsightItem(
                          context,
                          'Your most accurate persona extraction: ${(metrics.avgExtractionAccuracy * 100).toStringAsFixed(0)}%',
                        ),
                        const SizedBox(height: 8),
                        _buildInsightItem(
                          context,
                          'You\'ve recorded ${metrics.totalInteractions} interactions across ${metrics.totalPersonas} personas',
                        ),
                        const SizedBox(height: 8),
                        _buildInsightItem(
                          context,
                          'Keep recording more interactions to improve accuracy',
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetricCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 12),
            Text(
              value,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: Theme.of(context).textTheme.labelSmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailCard(
    BuildContext context, {
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(icon, size: 32, color: AppTheme.primaryColor),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  Text(
                    value,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppTheme.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInsightItem(BuildContext context, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(
            '•',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'Never';
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inSeconds < 60) {
      return 'Just now';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes} minutes ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours} hours ago';
    } else if (diff.inDays < 7) {
      return '${diff.inDays} days ago';
    } else {
      return date.toString().split(' ')[0];
    }
  }
}
