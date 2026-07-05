"""
SQLAlchemy Database Models
Defines User, QueryHistory, Session, and Experiment models for the application
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

Base = declarative_base()


# ============================================================================
# Role Constants
# ============================================================================
ROLE_ADMIN = 'admin'
ROLE_PARTICIPANT_CONTROL = 'participant_control'
ROLE_PARTICIPANT_EXPERIMENTAL = 'participant_experimental'

VALID_ROLES = [ROLE_ADMIN, ROLE_PARTICIPANT_CONTROL, ROLE_PARTICIPANT_EXPERIMENTAL]


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


class User(Base):
    """
    User model for authentication
    Stores user credentials and profile information

    Roles:
    - admin: Full access to dashboards, chatbot, and admin panel
    - participant_control: Dashboard access only (control group)
    - participant_experimental: Dashboard + chatbot access (experimental group)
    """
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default=ROLE_PARTICIPANT_CONTROL, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    query_history = relationship("QueryHistory", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    experiment_participant = relationship("ExperimentParticipant", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def can_access_chatbot(self) -> bool:
        """Check if user has access to chatbot (experimental group or admin)"""
        return self.role in (ROLE_ADMIN, ROLE_PARTICIPANT_EXPERIMENTAL)

    def can_access_dashboards(self) -> bool:
        """Check if user has access to dashboards (all roles)"""
        return self.role in VALID_ROLES

    def can_access_admin(self) -> bool:
        """Check if user has admin access"""
        return self.role == ROLE_ADMIN or self.is_admin


class QueryHistory(Base):
    """
    Query history model - Extended for thesis analysis
    Stores complete workflow: queries, SQL, results, visualizations, and all agent outputs
    """
    __tablename__ = "query_history"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ========================================================================
    # Query Information
    # ========================================================================
    user_query = Column(Text, nullable=False)
    domain = Column(String(50), nullable=True)  # sales, hr, production, etc.
    is_cross_departmental = Column(Boolean, default=False)  # Cross-domain query flag
    conversation_context = Column(JSON, nullable=True)  # Compressed conversation history used

    # ========================================================================
    # Orchestrator Output
    # ========================================================================
    orchestrator_action = Column(String(50), nullable=True)  # FULL_PIPELINE, DIRECT_ANSWER, etc.
    orchestrator_reasoning = Column(Text, nullable=True)  # Why this action was chosen
    needs_visualization = Column(Boolean, default=False)

    # ========================================================================
    # Schema Retrieval (RAG)
    # ========================================================================
    retrieved_tables = Column(JSON, nullable=True)  # List of table names
    anchor_tables = Column(JSON, nullable=True)  # List of anchor tables used
    rag_retrieved_tables = Column(JSON, nullable=True)  # Tables from RAG (excluding anchors)
    similarity_scores = Column(JSON, nullable=True)  # Dict of table: similarity score
    retrieval_strategy = Column(String(50), nullable=True)  # "anchor + rag" or "rag only"

    # ========================================================================
    # SQL Generation (with Chain-of-Thought)
    # ========================================================================
    generated_sql = Column(Text, nullable=True)
    sql_explanation = Column(Text, nullable=True)
    sql_reasoning_steps = Column(JSON, nullable=True)  # List of CoT reasoning steps
    tables_used = Column(JSON, nullable=True)  # Actual tables used in SQL (subset of retrieved)
    sql_assumptions = Column(JSON, nullable=True)  # Assumptions made during SQL generation
    sql_retry_count = Column(Integer, default=0)  # Number of retry attempts

    # ========================================================================
    # SQL Validation
    # ========================================================================
    validation_passed = Column(Boolean, nullable=True)
    validation_severity = Column(String(20), nullable=True)  # safe, warning, error, critical
    validation_issues = Column(JSON, nullable=True)  # List of validation issues found
    validation_summary = Column(Text, nullable=True)

    # ========================================================================
    # Query Execution
    # ========================================================================
    execution_status = Column(String(20), nullable=True)  # success, error, timeout
    execution_error = Column(Text, nullable=True)
    result_data = Column(JSON, nullable=True)  # Query results (actual data rows)
    row_count = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    # ========================================================================
    # Multi-Query Iteration (for complex queries)
    # ========================================================================
    query_iteration_count = Column(Integer, default=0)  # How many SQL queries executed
    needs_followup_query = Column(Boolean, default=False)  # Analyst determined more data needed
    followup_query_reason = Column(Text, nullable=True)  # Why follow-up was needed
    all_query_results = Column(JSON, nullable=True)  # Results from all iterations

    # ========================================================================
    # Analysis (Analyst Agent)
    # ========================================================================
    analysis = Column(Text, nullable=True)  # Full analysis JSON
    analysis_reasoning_steps = Column(JSON, nullable=True)  # Analyst CoT steps
    analysis_summary = Column(Text, nullable=True)  # One-sentence key finding
    key_insights = Column(JSON, nullable=True)  # List of bulleted insights
    recommendations = Column(JSON, nullable=True)  # Actionable recommendations
    data_quality_notes = Column(JSON, nullable=True)  # Caveats and limitations

    # ========================================================================
    # Visualization
    # ========================================================================
    chart_type = Column(String(50), nullable=True)  # bar, line, pie, scatter, table
    chart_config = Column(JSON, nullable=True)  # Complete chart configuration for frontend
    chart_reasoning = Column(Text, nullable=True)  # Why this chart type was selected
    visualization_code = Column(Text, nullable=True)  # Generated viz code (if applicable)
    chart_interpretation = Column(Text, nullable=True)  # Viz interpreter output (deprecated)

    # ========================================================================
    # Token Usage & Cost Tracking (for thesis analysis)
    # ========================================================================
    token_usage = Column(JSON, nullable=True)  # Detailed token usage per agent
    total_input_tokens = Column(Integer, nullable=True)  # Total input tokens
    total_output_tokens = Column(Integer, nullable=True)  # Total output tokens
    total_tokens = Column(Integer, nullable=True)  # Total tokens (input + output)
    total_cost_usd = Column(String(20), nullable=True)  # Total cost in USD (stored as string for precision)
    llm_calls_count = Column(Integer, nullable=True)  # Number of LLM API calls made

    # ========================================================================
    # Workflow Metadata (for thesis analysis)
    # ========================================================================
    workflow_id = Column(String(36), nullable=True)  # Unique workflow execution ID
    workflow_started_at = Column(DateTime(timezone=True), nullable=True)  # Workflow start time
    workflow_completed_at = Column(DateTime(timezone=True), nullable=True)  # Workflow end time
    total_duration_ms = Column(Integer, nullable=True)  # Total workflow duration
    error_occurred = Column(Boolean, default=False)  # Whether any error occurred
    error_stage = Column(String(50), nullable=True)  # Which agent failed (if error)
    error_details = Column(Text, nullable=True)  # Detailed error information

    # ========================================================================
    # Experiment Tracking (links to experiment tasks for experimental group)
    # ========================================================================
    experiment_task_id = Column(String(36), ForeignKey("public.experiment_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    # Direct link to participant for history filtering (multiple participants share same user account)
    participant_id = Column(String(36), ForeignKey("public.experiment_participants.id", ondelete="SET NULL"), nullable=True, index=True)

    # ========================================================================
    # Metadata
    # ========================================================================
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="query_history")
    experiment_task = relationship("ExperimentTask", back_populates="query_history")
    participant = relationship("ExperimentParticipant", back_populates="query_history")

    def __repr__(self):
        return f"<QueryHistory(id={self.id}, user_id={self.user_id}, query={self.user_query[:50]}...)>"


class Session(Base):
    """
    Session model for tracking user sessions
    Stores active JWT tokens and session metadata
    """
    __tablename__ = "sessions"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session information
    token = Column(String(500), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)

    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    def is_expired(self):
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at


# ============================================================================
# EXPERIMENT MODELS
# ============================================================================

class Experiment(Base):
    """
    Experiment model - Study-level metadata
    Stores experiment configuration and design parameters
    """
    __tablename__ = "experiments"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Experiment Information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    research_question = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)

    # Study Design
    study_type = Column(String(50), default='user_study')
    design_type = Column(String(50), default='between_subjects')

    # Experimental Conditions
    control_condition_name = Column(String(100), default='BI Dashboard (Control)')
    experimental_condition_name = Column(String(100), default='Dashboard + Conversational AI (Experimental)')
    control_description = Column(Text, nullable=True)
    experimental_description = Column(Text, nullable=True)

    # IRB/Ethics
    irb_approval_number = Column(String(100), nullable=True)
    consent_form_version = Column(String(50), nullable=True)
    ethics_approved = Column(Boolean, default=False)
    anonymization_level = Column(String(50), default='full')

    # Timeline
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(DateTime(timezone=True), nullable=True)
    actual_end_date = Column(DateTime(timezone=True), nullable=True)

    # Sample Size
    target_participants_per_group = Column(Integer, default=15)
    actual_control_participants = Column(Integer, default=0)
    actual_experimental_participants = Column(Integer, default=0)

    # Monotonic counter used by ExperimentService.generate_participant_code.
    # Survives row deletions so codes are never reused.
    next_participant_number = Column(Integer, nullable=False, default=1)

    # System Configuration
    system_version = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    optimization_settings = Column(JSON, nullable=True)

    # Task Design
    total_tasks = Column(Integer, nullable=True)
    task_definitions = Column(JSON, nullable=True)

    # Status
    status = Column(String(50), default='planning')

    # Metadata
    created_by = Column(String(36), ForeignKey("public.users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    participants = relationship("ExperimentParticipant", back_populates="experiment", cascade="all, delete-orphan")
    tasks = relationship("ExperimentTask", back_populates="experiment", cascade="all, delete-orphan")
    interactions = relationship("ExperimentInteraction", back_populates="experiment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Experiment(id={self.id}, name={self.name}, status={self.status})>"


class ExperimentParticipant(Base):
    """
    Experiment Participant model
    Stores participant demographics and experimental condition assignment

    NOTE: No personally identifiable information (PII) is collected.
    Only anonymous demographic data from pre-survey is stored.
    """
    __tablename__ = "experiment_participants"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Link to Experiment
    experiment_id = Column(String(36), ForeignKey("public.experiments.id", ondelete="CASCADE"), nullable=False, index=True)

    # Participant Identification (anonymous)
    participant_code = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Recruitment Tracking (migration 008)
    # Where the participant came from. 'university' for pre-Prolific cohort
    # (CSS masters + university invitation email) and manually enrolled users;
    # 'prolific' set automatically when PROLIFIC_PID is present at registration.
    recruitment_source = Column(String(20), default='university', nullable=True)
    prolific_pid = Column(String(100), nullable=True, unique=True)
    prolific_study_id = Column(String(100), nullable=True)
    prolific_session_id = Column(String(100), nullable=True)

    # Registration Tracking
    registered_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    # ========================================================================
    # Pre-Survey Questions (7 questions - all anonymous, no PII)
    # ========================================================================
    # Q1: Age (exact, in years)
    age = Column(Integer, nullable=True)  # Exact age in years (18-99)
    age_range = Column(String(50), nullable=True)  # Legacy - kept for existing data

    # Q2: Occupation Status (multi-select, comma-separated)
    occupation_statuses = Column(String(200), nullable=True)  # e.g. "student,employee"
    occupation_status = Column(String(50), nullable=True)  # Legacy - kept for existing data

    # Q3: Field of Work/Study (conditional based on occupation)
    field_of_work = Column(String(100), nullable=True)  # Shown when employee/self_employed/other selected
    field_of_study = Column(String(100), nullable=True)  # Shown when student selected

    # Q4: Visual Analytics Frequency
    visual_analytics_frequency = Column(String(50), nullable=True)  # "never", "rarely", "occasionally", "regularly", "daily"

    # Q5: Business Background
    business_background = Column(String(100), nullable=True)  # "education", "experience", "both", "none"

    # Q6: LLM Chatbot Experience
    llm_chatbot_experience = Column(String(50), nullable=True)  # "never", "once_twice", "occasionally", "regularly"

    # Q7: BI Tools Experience
    bi_tools_experience = Column(String(50), nullable=True)  # "none", "minimal", "basic", "intermediate", "advanced"

    # ========================================================================
    # Legacy fields (kept for backward compatibility, no longer collected)
    # ========================================================================
    age_group = Column(String(50), nullable=True)  # Legacy - use age_range instead
    gender = Column(String(50), nullable=True)  # No longer collected
    education_level = Column(String(100), nullable=True)  # No longer collected
    occupation = Column(String(100), nullable=True)  # Legacy - use occupation_status
    industry = Column(String(100), nullable=True)  # No longer collected
    sql_proficiency = Column(String(50), nullable=True)  # No longer collected
    data_analysis_experience_years = Column(Integer, nullable=True)  # No longer collected
    email_hash = Column(String(255), nullable=True)  # No longer collected

    # ========================================================================
    # Consent & Privacy
    # ========================================================================
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    data_retention_until = Column(Date, nullable=True)
    withdrawal_requested = Column(Boolean, default=False)
    withdrawal_timestamp = Column(DateTime(timezone=True), nullable=True)
    # Free-text audit trail of manual admin interventions (migration 011)
    admin_notes = Column(Text, nullable=True)

    # Experimental Assignment (Between-Subjects)
    condition_assigned = Column(String(50), nullable=False)  # 'control' or 'experimental'
    assignment_method = Column(String(50), default='random')
    randomization_seed = Column(Integer, nullable=True)
    assignment_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Pre-Study Baseline
    baseline_survey_responses = Column(JSON, nullable=True)
    baseline_technical_test_score = Column(Float, nullable=True)

    # Post-Study Measures
    post_study_survey_responses = Column(JSON, nullable=True)

    # Usability Metrics (Experimental Group)
    system_usability_scale_score = Column(Float, nullable=True)
    chatbot_understanding_rating = Column(Integer, nullable=True)
    explanation_helpfulness_rating = Column(Integer, nullable=True)
    sql_trust_rating = Column(Integer, nullable=True)
    overall_satisfaction_rating = Column(Integer, nullable=True)
    would_use_at_work = Column(Boolean, nullable=True)

    # User Experience Metrics
    perceived_usefulness = Column(Integer, nullable=True)
    perceived_ease_of_use = Column(Integer, nullable=True)
    frustration_level = Column(Integer, nullable=True)
    confidence_in_results = Column(Integer, nullable=True)

    # Completion Status
    session_completed = Column(Boolean, default=False)
    session_completed_at = Column(DateTime(timezone=True), nullable=True)
    tasks_completed = Column(Integer, default=0)
    tasks_attempted = Column(Integer, default=0)

    # Status
    status = Column(String(50), default='recruited')
    exclusion_reason = Column(Text, nullable=True)

    # Metadata
    recruited_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    first_task_at = Column(DateTime(timezone=True), nullable=True)
    last_task_at = Column(DateTime(timezone=True), nullable=True)
    total_session_duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="participants")
    user = relationship("User", back_populates="experiment_participant")
    tasks = relationship("ExperimentTask", back_populates="participant", cascade="all, delete-orphan")
    interactions = relationship("ExperimentInteraction", back_populates="participant", cascade="all, delete-orphan")
    query_history = relationship("QueryHistory", back_populates="participant")

    def __repr__(self):
        return f"<ExperimentParticipant(id={self.id}, code={self.participant_code}, condition={self.condition_assigned})>"


class ExperimentTask(Base):
    """
    Experiment Task model
    Stores task-level performance data for each participant
    """
    __tablename__ = "experiment_tasks"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Links
    experiment_id = Column(String(36), ForeignKey("public.experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(String(36), ForeignKey("public.experiment_participants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Task Definition
    task_id = Column(String(100), nullable=False, index=True)
    task_number = Column(Integer, nullable=False)

    # Task Description
    task_description = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=True)
    domain = Column(String(50), nullable=True)
    complexity_level = Column(String(50), nullable=True)

    # Tutorial Fields
    is_tutorial = Column(Boolean, default=False)
    tutorial_steps = Column(Text, nullable=True)
    tutorial_tips = Column(Text, nullable=True)

    # Success Criteria
    expected_insights = Column(JSON, nullable=True)
    success_criteria = Column(JSON, nullable=True)

    # Timing (PRIMARY OUTCOME 1)
    task_started_at = Column(DateTime(timezone=True), nullable=True)
    task_completed_at = Column(DateTime(timezone=True), nullable=True)
    task_duration_seconds = Column(Integer, nullable=True)

    # Participant Submission
    submitted_answer = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Answer Quality (PRIMARY OUTCOME 2)
    answer_completeness_score = Column(Float, nullable=True)
    answer_accuracy_score = Column(Float, nullable=True)
    answer_depth_score = Column(Float, nullable=True)
    overall_answer_quality_score = Column(Float, nullable=True)

    # Process Efficiency (PRIMARY OUTCOME 3)
    total_interactions = Column(Integer, default=0)
    queries_executed = Column(Integer, default=0)
    dashboard_interactions = Column(Integer, default=0)
    got_stuck = Column(Boolean, default=False)
    gave_up_on_task = Column(Boolean, default=False)
    help_requested = Column(Boolean, default=False)

    # Conversational AI Specific (Experimental Group Only)
    chatbot_queries = Column(JSON, nullable=True)
    chatbot_query_count = Column(Integer, default=0)
    sql_queries_generated = Column(JSON, nullable=True)
    visualization_types_used = Column(JSON, nullable=True)

    # Task Outcome
    task_successful = Column(Boolean, nullable=True)
    partial_success = Column(Boolean, default=False)
    task_abandoned = Column(Boolean, default=False)
    abandonment_reason = Column(Text, nullable=True)

    # Error Tracking
    errors_encountered = Column(JSON, nullable=True)
    technical_issues = Column(Text, nullable=True)

    # Participant Feedback
    task_difficulty_rating = Column(Integer, nullable=True)
    confidence_in_answer = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    experiment = relationship("Experiment", back_populates="tasks")
    participant = relationship("ExperimentParticipant", back_populates="tasks")
    interactions = relationship("ExperimentInteraction", back_populates="task", cascade="all, delete-orphan")
    query_history = relationship("QueryHistory", back_populates="experiment_task")

    def __repr__(self):
        return f"<ExperimentTask(id={self.id}, task_id={self.task_id}, participant_id={self.participant_id})>"


class ExperimentInteraction(Base):
    """
    Experiment Interaction model
    Detailed log of user interactions during task completion
    """
    __tablename__ = "experiment_interactions"
    __table_args__ = {"schema": "public"}

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Links
    experiment_id = Column(String(36), ForeignKey("public.experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(String(36), ForeignKey("public.experiment_participants.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("public.experiment_tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Interaction Metadata
    interaction_sequence = Column(Integer, nullable=False)
    interaction_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Interaction Type
    interaction_type = Column(String(50), nullable=False, index=True)

    # Chatbot Interaction (if applicable)
    user_query = Column(Text, nullable=True)
    system_response = Column(JSON, nullable=True)
    query_understood = Column(Boolean, nullable=True)
    query_successful = Column(Boolean, nullable=True)

    # Dashboard Interaction (if applicable)
    dashboard_action = Column(String(100), nullable=True)
    dashboard_element = Column(String(100), nullable=True)

    # Token/Cost Tracking
    tokens_used = Column(Integer, nullable=True)
    cost_usd = Column(String(20), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    experiment = relationship("Experiment", back_populates="interactions")
    participant = relationship("ExperimentParticipant", back_populates="interactions")
    task = relationship("ExperimentTask", back_populates="interactions")

    def __repr__(self):
        return f"<ExperimentInteraction(id={self.id}, type={self.interaction_type}, sequence={self.interaction_sequence})>"


# Export all models
__all__ = [
    "Base",
    "User",
    "QueryHistory",
    "Session",
    "Experiment",
    "ExperimentParticipant",
    "ExperimentTask",
    "ExperimentInteraction",
    "ROLE_ADMIN",
    "ROLE_PARTICIPANT_CONTROL",
    "ROLE_PARTICIPANT_EXPERIMENTAL",
    "VALID_ROLES",
]
