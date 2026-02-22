import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/app_providers.dart';

/// Screen for recording interactions with audio
class RecordInteractionScreen extends ConsumerStatefulWidget {
  const RecordInteractionScreen({super.key});

  @override
  ConsumerState<RecordInteractionScreen> createState() => _RecordInteractionScreenState();
}

class _RecordInteractionScreenState extends ConsumerState<RecordInteractionScreen> {
  Timer? _timer;
  int _secondsElapsed = 0;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final recordingState = ref.watch(recordingStateProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Record Interaction'),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const SizedBox(height: 48),
              // Recording indicator
              if (recordingState.isRecording)
                _buildRecordingIndicator(context)
              else
                _buildWaveformDisplay(context),
              const SizedBox(height: 48),
              // Timer
              Text(
                _formatDuration(_secondsElapsed),
                style: Theme.of(context).textTheme.displaySmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              // Mode selector
              if (!recordingState.isRecording)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Interaction Mode',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            child: ChoiceChip(
                              label: const Text('LIVE'),
                              selected: recordingState.mode == RecordingMode.live,
                              onSelected: (selected) {
                                if (selected) {
                                  ref.read(recordingStateProvider.notifier).state = recordingState.copyWith(
                                    mode: RecordingMode.live,
                                  );
                                }
                              },
                            ),
                          ),
                        ),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 4),
                            child: ChoiceChip(
                              label: const Text('RECAP'),
                              selected: recordingState.mode == RecordingMode.recap,
                              onSelected: (selected) {
                                if (selected) {
                                  ref.read(recordingStateProvider.notifier).state = recordingState.copyWith(
                                    mode: RecordingMode.recap,
                                  );
                                }
                              },
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              // Recording controls
              recordingState.isRecording
                  ? _buildRecordingControls(context, recordingState)
                  : _buildStartControls(context),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWaveformDisplay(BuildContext context) {
    return Container(
      height: 150,
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Center(
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            30,
            (index) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Container(
                width: 4,
                height: 30 + (index % 15).toDouble() * 2,
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRecordingIndicator(BuildContext context) {
    return Column(
      children: [
        Container(
          height: 150,
          decoration: BoxDecoration(
            color: Colors.red.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.red, width: 2),
          ),
          child: Center(
            child: AnimatedBuilder(
              animation: AlwaysStoppedAnimation(DateTime.now().millisecond / 1000),
              builder: (context, child) => Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.red,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.red.withValues(alpha: 0.5),
                      blurRadius: 10,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.mic,
                  color: Colors.white,
                  size: 40,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.red,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              'Recording...',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRecordingControls(
    BuildContext context,
    RecordingState recordingState,
  ) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        FloatingActionButton(
          heroTag: 'cancel',
          backgroundColor: Colors.grey,
          onPressed: () {
            _timer?.cancel();
            setState(() => _secondsElapsed = 0);
            ref.read(recordingStateProvider.notifier).state = RecordingState(
              isRecording: false,
            );
          },
          child: const Icon(Icons.close),
        ),
        FloatingActionButton.large(
          heroTag: 'stop',
          backgroundColor: Colors.red,
          onPressed: () async {
            _timer?.cancel();
            final filePath = recordingState.filePath;
            if (filePath != null) {
              _processRecording(filePath);
            }
          },
          child: const Icon(Icons.stop, color: Colors.white),
        ),
      ],
    );
  }

  Widget _buildStartControls(BuildContext context) {
    return FloatingActionButton.large(
      heroTag: 'record',
      backgroundColor: AppTheme.primaryColor,
      onPressed: _startRecording,
      child: const Icon(Icons.mic, color: Colors.white, size: 32),
    );
  }

  void _startRecording() {
    setState(() => _secondsElapsed = 0);
    ref.read(recordingStateProvider.notifier).state = RecordingState(
      isRecording: true,
      filePath: 'recording_${DateTime.now().millisecondsSinceEpoch}.wav',
    );

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() => _secondsElapsed++);
    });
  }

  void _processRecording(String filePath) async {
    ref.read(recordingStateProvider.notifier).state = RecordingState(
      isRecording: false,
      isProcessing: true,
    );

    try {
      // TODO: Implement actual audio file upload
      await Future.delayed(const Duration(seconds: 2)); // Simulate processing

      if (mounted) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Processing Complete'),
            content: const Text(
              'Your interaction has been recorded and synapses are being extracted.',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pop(context);
                },
                child: const Text('Done'),
              ),
            ],
          ),
        );

        ref.read(recordingStateProvider.notifier).state = RecordingState(
          isRecording: false,
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }
}
