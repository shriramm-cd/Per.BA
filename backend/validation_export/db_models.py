from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.db.postgres import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class ValidationResultDB(Base):
    __tablename__ = "validation_results"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    quality_score = Column(Float, nullable=False)
    coverage_score = Column(Float, nullable=False)
    traceability_score = Column(Float, nullable=False)
    decision = Column(String(50), nullable=False)  # PASS, REWORK, MANUAL_REVIEW
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Validation reporting metrics
    validators_passed = Column(Integer, default=0)
    validators_failed = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    major_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)

    # Audit and versioning
    version_number = Column(Integer, default=1)
    execution_id = Column(String(36), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=True)

    findings = relationship("ValidationFindingDB", back_populates="validation_result", cascade="all, delete-orphan")


class ValidationFindingDB(Base):
    __tablename__ = "validation_findings"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    validation_result_id = Column(String(36), ForeignKey("validation_results.id", ondelete="CASCADE"), nullable=False)
    validator_name = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # CRITICAL, MAJOR, MINOR, INFO
    field = Column(String(100), nullable=True)
    mitigation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Audit and versioning
    version_number = Column(Integer, default=1)
    execution_id = Column(String(36), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=True)

    validation_result = relationship("ValidationResultDB", back_populates="findings")


class BAReviewDB(Base):
    __tablename__ = "ba_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    reviewer = Column(String(255), nullable=False)
    decision = Column(String(50), nullable=False)  # APPROVE, REWORK, REJECT
    comments = Column(Text, nullable=True)
    edits = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Audit and versioning
    version_number = Column(Integer, default=1)
    execution_id = Column(String(36), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=True)


class AuditEventDB(Base):
    __tablename__ = "audit_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)  # VALIDATION_STARTED, etc.
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class RevisionPackageDB(Base):
    __tablename__ = "revision_packages"
    __table_args__ = {'extend_existing': True}

    package_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    retry_count = Column(Integer, nullable=False)
    failed_validators = Column(JSON, nullable=False)
    validation_report = Column(JSON, nullable=False)
    ba_comments = Column(Text, nullable=True)
    preserve_section = Column(JSON, nullable=False)
    modify_section = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Audit and versioning
    version_number = Column(Integer, default=1)
    execution_id = Column(String(36), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=True)


class ValidatedStoryPackageDB(Base):
    __tablename__ = "validated_story_packages"
    __table_args__ = {'extend_existing': True}

    package_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    stories = Column(JSON, nullable=False)
    traceability_links = Column(JSON, nullable=False)
    coverage_metrics = Column(JSON, nullable=False)
    quality_metrics = Column(JSON, nullable=False)
    approval_status = Column(String(50), nullable=False)
    audit_metadata = Column(JSON, nullable=False)
    final_story_zest = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Audit and versioning
    version_number = Column(Integer, default=1)
    execution_id = Column(String(36), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=True)
