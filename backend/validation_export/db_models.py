from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.db.postgres import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class ValidationResultDB(Base):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    quality_score = Column(Float, nullable=False)
    coverage_score = Column(Float, nullable=False)
    traceability_score = Column(Float, nullable=False)
    decision = Column(String(50), nullable=False)  # PASS, REWORK, MANUAL_REVIEW
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    findings = relationship("ValidationFindingDB", back_populates="validation_result", cascade="all, delete-orphan")


class ValidationFindingDB(Base):
    __tablename__ = "validation_findings"

    id = Column(String(36), primary_key=True)
    validation_result_id = Column(String(36), ForeignKey("validation_results.id", ondelete="CASCADE"), nullable=False)
    validator_name = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # CRITICAL, MAJOR, MINOR, INFO
    field = Column(String(100), nullable=True)
    mitigation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    validation_result = relationship("ValidationResultDB", back_populates="findings")


class BAReviewDB(Base):
    __tablename__ = "ba_reviews"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    reviewer = Column(String(255), nullable=False)
    decision = Column(String(50), nullable=False)  # APPROVE, REWORK, REJECT
    comments = Column(Text, nullable=True)
    edits = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class AuditEventDB(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)  # VALIDATION_STARTED, etc.
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class RevisionPackageDB(Base):
    __tablename__ = "revision_packages"

    package_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    retry_count = Column(Integer, nullable=False)
    failed_validators = Column(JSON, nullable=False)
    validation_report = Column(JSON, nullable=False)
    ba_comments = Column(Text, nullable=True)
    preserve_section = Column(JSON, nullable=False)
    modify_section = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)


class ValidatedStoryPackageDB(Base):
    __tablename__ = "validated_story_packages"

    package_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    stories = Column(JSON, nullable=False)
    traceability_links = Column(JSON, nullable=False)
    coverage_metrics = Column(JSON, nullable=False)
    quality_metrics = Column(JSON, nullable=False)
    approval_status = Column(String(50), nullable=False)
    audit_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
