/// Domain entities for Linkd app

class User {
  final int id;
  final String email;
  final DateTime createdAt;

  User({
    required this.id,
    required this.email,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'created_at': createdAt.toIso8601String(),
  };
}

class Persona {
  final int id;
  final int? userId;
  final String label;
  final double weight;
  final double? confidenceScore;
  final DateTime? createdAt;
  final List<String>? feedbackHistory;

  Persona({
    required this.id,
    this.userId,
    required this.label,
    required this.weight,
    this.confidenceScore,
    this.createdAt,
    this.feedbackHistory,
  });

  factory Persona.fromJson(Map<String, dynamic> json) {
    return Persona(
      id: json['id'],
      userId: json['user_id'],
      label: json['label'],
      weight: (json['weight'] is num) ? (json['weight'] as num).toDouble() : (json['weight'] ?? 1).toDouble(),
      confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'label': label,
    'weight': weight,
    'confidence_score': confidenceScore,
  };

  Persona copyWith({
    int? id,
    int? userId,
    String? label,
    double? weight,
    double? confidenceScore,
    DateTime? createdAt,
  }) {
    return Persona(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      label: label ?? this.label,
      weight: weight ?? this.weight,
      confidenceScore: confidenceScore ?? this.confidenceScore,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}

class Synapse {
  final int personaId;
  final String personaLabel;
  final double similarity;
  final int rank;

  Synapse({
    required this.personaId,
    required this.personaLabel,
    required this.similarity,
    required this.rank,
  });

  factory Synapse.fromJson(Map<String, dynamic> json) {
    return Synapse(
      personaId: json['persona_id'],
      personaLabel: json['persona_label'],
      similarity: (json['similarity'] as num).toDouble(),
      rank: json['rank'],
    );
  }

  Map<String, dynamic> toJson() => {
    'persona_id': personaId,
    'persona_label': personaLabel,
    'similarity': similarity,
    'rank': rank,
  };
}

class Interaction {
  final int id;
  final int userId;
  final String mode; // "live" or "recap"
  final String? transcriptExcerpt;
  final List<Synapse>? topSynapses;
  final DateTime createdAt;
  final String? extractedInterests;

  Interaction({
    required this.id,
    required this.userId,
    required this.mode,
    this.transcriptExcerpt,
    this.topSynapses,
    required this.createdAt,
    this.extractedInterests,
  });

  factory Interaction.fromJson(Map<String, dynamic> json) {
    return Interaction(
      id: json['id'],
      userId: json['user_id'],
      mode: json['mode'],
      transcriptExcerpt: json['transcript_excerpt'],
      topSynapses: (json['top_synapses'] as List?)
          ?.map((e) => Synapse.fromJson(e))
          .toList(),
      createdAt: DateTime.parse(json['created_at']),
      extractedInterests: json['extracted_interests'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'mode': mode,
    'transcript_excerpt': transcriptExcerpt,
    'top_synapses': topSynapses?.map((e) => e.toJson()).toList(),
    'created_at': createdAt.toIso8601String(),
    'extracted_interests': extractedInterests,
  };
}

class Job {
  final String id;
  final String status; // "pending", "processing", "completed", "failed"
  final int progress; // 0-100
  final String jobType; // "onboarding", "interaction"
  final dynamic result;
  final String? errorMessage;
  final DateTime? createdAt;
  final DateTime? startedAt;
  final DateTime? completedAt;

  Job({
    required this.id,
    required this.status,
    required this.progress,
    required this.jobType,
    this.result,
    this.errorMessage,
    this.createdAt,
    this.startedAt,
    this.completedAt,
  });

  factory Job.fromJson(Map<String, dynamic> json) {
    return Job(
      id: json['job_id'],
      status: json['status'],
      progress: json['progress'] ?? 0,
      jobType: json['job_type'],
      result: json['result'],
      errorMessage: json['error_message'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,
      startedAt: json['started_at'] != null 
          ? DateTime.parse(json['started_at']) 
          : null,
      completedAt: json['completed_at'] != null 
          ? DateTime.parse(json['completed_at']) 
          : null,
    );
  }

  bool get isComplete => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isProcessing => status == 'processing' || status == 'pending';
}

class Metrics {
  final int totalInteractions;
  final int totalPersonas;
  final String? topPersona;
  final double avgExtractionAccuracy;
  final double approvalRate;
  final double avgProcessingTimeMs;
  final double avgTopSimilarity;
  final int totalApproved;
  final int totalRejected;
  final double? avgInteractionLength;
  final DateTime? lastInteractionAt;

  Metrics({
    required this.totalInteractions,
    this.totalPersonas = 0,
    this.topPersona,
    required this.avgExtractionAccuracy,
    required this.approvalRate,
    required this.avgProcessingTimeMs,
    required this.avgTopSimilarity,
    required this.totalApproved,
    required this.totalRejected,
    this.avgInteractionLength,
    this.lastInteractionAt,
  });

  factory Metrics.fromJson(Map<String, dynamic> json) {
    return Metrics(
      totalInteractions: json['total_interactions'] ?? 0,
      totalPersonas: json['total_personas'] ?? 0,
      topPersona: json['top_persona'],
      avgExtractionAccuracy: (json['avg_extraction_accuracy'] as num?)?.toDouble() ?? 0.0,
      approvalRate: (json['approval_rate'] as num?)?.toDouble() ?? 0.0,
      avgProcessingTimeMs: (json['avg_processing_time_ms'] as num?)?.toDouble() ?? 0.0,
      avgTopSimilarity: (json['avg_top_similarity'] as num?)?.toDouble() ?? 0.0,
      totalApproved: json['total_approved'] ?? 0,
      totalRejected: json['total_rejected'] ?? 0,
      avgInteractionLength: (json['avg_interaction_length'] as num?)?.toDouble(),
      lastInteractionAt: json['last_interaction_at'] != null 
        ? DateTime.parse(json['last_interaction_at'])
        : null,
    );
  }
}

class AuthResponse {
  final User user;
  final String token;
  final bool isNewUser;

  AuthResponse({
    required this.user,
    required this.token,
    required this.isNewUser,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      user: User.fromJson(json['user']),
      token: json['token'],
      isNewUser: json['is_new_user'] ?? false,
    );
  }
}
