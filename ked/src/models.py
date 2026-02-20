from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, func, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    personas = relationship("UserPersona", back_populates="user")
    interest_nodes = relationship("InterestNode", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")


class UserPersona(Base):
    __tablename__ = "user_persona"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    weight = Column(Integer, default=1)
    vector = Column(Vector(1536))

    user = relationship("User", back_populates="personas")


class InterestNode(Base):
    __tablename__ = "interest_nodes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    vector = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interest_nodes")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transcript = Column(Text)
    metadata = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="conversations")


class Job(Base):
    """Async job tracking for long-running tasks."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="pending", index=True)  # pending, processing, completed, failed, cancelled
    job_type = Column(String, nullable=False)  # "onboarding", "interaction", etc.
    input_data = Column(Text)  # JSON-serialized input
    result = Column(Text)  # JSON-serialized result
    error_message = Column(Text)  # Error details if failed
    job_metadata = Column(Text)  # JSON-serialized metadata (celery_task_id, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress = Column(Integer, default=0)  # 0-100%


class PersonaFeedback(Base):
    """User feedback on persona nodes (approve/reject/rate)."""
    __tablename__ = "persona_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(Integer, ForeignKey("user_persona.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = Column(String, nullable=False)  # "approved", "rejected", "rated"
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InteractionMetric(Base):
    """Metrics for tracking accuracy and performance."""
    __tablename__ = "interaction_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String, nullable=False)  # "live" or "recap"
    top_synapse_similarity = Column(Float)  # Best match score
    avg_similarity = Column(Float)  # Average of top 3
    extraction_accuracy = Column(Float)  # % of correct interests identified
    processing_time_ms = Column(Integer)  # Total processing time
    user_approved = Column(Integer, default=0)  # Number of approved synapses
    user_rejected = Column(Integer, default=0)  # Number of rejected synapses
    created_at = Column(DateTime(timezone=True), server_default=func.now())
