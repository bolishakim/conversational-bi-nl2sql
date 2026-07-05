-- ============================================================================
-- NL2SQL Thesis Application - Complete Database Setup Script
-- ============================================================================
-- This script creates all necessary database objects for the NL2SQL thesis project.
-- Run this script on a fresh PostgreSQL database with pgvector extension installed.
--
-- Prerequisites:
--   1. PostgreSQL 14+ with pgvector extension
--   2. A database named "Adventureworks" (or change DATABASE_NAME in .env)
--   3. Run this script as a user with CREATE privileges
--
-- Usage:
--   psql -h localhost -U your_user -d Adventureworks -f setup_database.sql
--
-- Date: 2025-01-10
-- ============================================================================

-- ============================================================================
-- 0. EXTENSIONS AND SCHEMAS
-- ============================================================================

-- Enable pgvector extension for RAG embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create RAG schema for embeddings
CREATE SCHEMA IF NOT EXISTS rag;

-- ============================================================================
-- 1. USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    role VARCHAR(50) DEFAULT 'participant_control' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);

COMMENT ON TABLE public.users IS 'User accounts for authentication';
COMMENT ON COLUMN public.users.role IS 'User role: admin, participant_control (dashboard only), participant_experimental (dashboard + chatbot)';

-- ============================================================================
-- 2. SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id VARCHAR(36) NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON public.sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON public.sessions(expires_at);

COMMENT ON TABLE public.sessions IS 'Active user sessions with JWT tokens';

-- ============================================================================
-- 3. EXPERIMENTS TABLE (Study-Level Metadata)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiments (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Experiment Information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    research_question TEXT,
    hypothesis TEXT,

    -- Study Design (Between-Subjects)
    study_type VARCHAR(50) DEFAULT 'user_study',
    design_type VARCHAR(50) DEFAULT 'between_subjects',

    -- Experimental Conditions
    control_condition_name VARCHAR(100) DEFAULT 'BI Dashboard (Control)',
    experimental_condition_name VARCHAR(100) DEFAULT 'Dashboard + Conversational AI (Experimental)',
    control_description TEXT,
    experimental_description TEXT,

    -- IRB/Ethics
    irb_approval_number VARCHAR(100),
    consent_form_version VARCHAR(50),
    ethics_approved BOOLEAN DEFAULT FALSE,
    anonymization_level VARCHAR(50) DEFAULT 'full',

    -- Timeline
    planned_start_date DATE,
    planned_end_date DATE,
    actual_start_date TIMESTAMP WITH TIME ZONE,
    actual_end_date TIMESTAMP WITH TIME ZONE,

    -- Sample Size
    target_participants_per_group INTEGER DEFAULT 15,
    actual_control_participants INTEGER DEFAULT 0,
    actual_experimental_participants INTEGER DEFAULT 0,

    -- System Configuration
    system_version VARCHAR(50),
    llm_model VARCHAR(100),
    optimization_settings JSON,

    -- Task Design
    total_tasks INTEGER,
    task_definitions JSON,

    -- Status
    status VARCHAR(50) DEFAULT 'planning',

    -- Metadata
    created_by VARCHAR(36) REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_experiments_status ON public.experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_dates ON public.experiments(actual_start_date, actual_end_date);

COMMENT ON TABLE public.experiments IS 'Study-level metadata for between-subjects user experiments';
COMMENT ON COLUMN public.experiments.control_description IS 'Traditional BI dashboard with pre-built visualizations, filtering, drill-down, complete documentation';
COMMENT ON COLUMN public.experiments.experimental_description IS 'Same BI dashboard + integrated conversational chatbot with NL queries, SQL explanations, contextual interpretations';

-- ============================================================================
-- 4. EXPERIMENT_PARTICIPANTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_participants (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Link to Experiment
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,

    -- Participant Identification (Anonymized)
    participant_code VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(36) REFERENCES public.users(id) ON DELETE SET NULL,

    -- Onboarding Fields (collected during registration)
    full_name VARCHAR(255),
    phone_number VARCHAR(50),
    date_of_birth DATE,
    job_role VARCHAR(100),
    job_title VARCHAR(255),
    company_name VARCHAR(255),
    field_of_study VARCHAR(255),
    university_name VARCHAR(255),
    registered_at TIMESTAMP WITH TIME ZONE,
    onboarding_completed BOOLEAN DEFAULT FALSE,

    -- Demographics
    age_group VARCHAR(50),
    gender VARCHAR(50),
    education_level VARCHAR(100),
    occupation VARCHAR(100),
    industry VARCHAR(100),

    -- Technical Background
    sql_proficiency VARCHAR(50),
    bi_tools_experience VARCHAR(50),
    data_analysis_experience_years INTEGER,

    -- Contact (encrypted/hashed for privacy)
    email_hash VARCHAR(255),

    -- Consent & Privacy
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_until DATE,
    withdrawal_requested BOOLEAN DEFAULT FALSE,
    withdrawal_timestamp TIMESTAMP WITH TIME ZONE,

    -- Experimental Assignment (Between-Subjects)
    condition_assigned VARCHAR(50) NOT NULL,
    assignment_method VARCHAR(50) DEFAULT 'random',
    randomization_seed INTEGER,
    assignment_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Pre-Study Baseline
    baseline_survey_responses JSON,
    baseline_technical_test_score FLOAT,

    -- Post-Study Measures
    post_study_survey_responses JSON,

    -- Usability Metrics (Experimental Group)
    system_usability_scale_score FLOAT,
    chatbot_understanding_rating INTEGER,
    explanation_helpfulness_rating INTEGER,
    sql_trust_rating INTEGER,
    overall_satisfaction_rating INTEGER,
    would_use_at_work BOOLEAN,

    -- User Experience Metrics
    perceived_usefulness INTEGER,
    perceived_ease_of_use INTEGER,
    frustration_level INTEGER,
    confidence_in_results INTEGER,

    -- Completion Status
    session_completed BOOLEAN DEFAULT FALSE,
    session_completed_at TIMESTAMP WITH TIME ZONE,
    tasks_completed INTEGER DEFAULT 0,
    tasks_attempted INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'recruited',
    exclusion_reason TEXT,

    -- Metadata
    recruited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_task_at TIMESTAMP WITH TIME ZONE,
    last_task_at TIMESTAMP WITH TIME ZONE,
    total_session_duration_minutes INTEGER,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_exp_participants_experiment ON public.experiment_participants(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_participants_code ON public.experiment_participants(participant_code);
CREATE INDEX IF NOT EXISTS idx_exp_participants_condition ON public.experiment_participants(condition_assigned);
CREATE INDEX IF NOT EXISTS idx_exp_participants_status ON public.experiment_participants(status);
CREATE INDEX IF NOT EXISTS idx_exp_participants_name_dob ON public.experiment_participants(full_name, date_of_birth);
CREATE INDEX IF NOT EXISTS idx_participants_condition_status ON public.experiment_participants(condition_assigned, status);

COMMENT ON TABLE public.experiment_participants IS 'Participant demographics and experimental condition assignment';
COMMENT ON COLUMN public.experiment_participants.condition_assigned IS 'Between-subjects assignment: control or experimental';
COMMENT ON COLUMN public.experiment_participants.sql_proficiency IS 'Varying levels intentional: system meant for both data analysts and business users';
COMMENT ON COLUMN public.experiment_participants.full_name IS 'Participant full name for identification';
COMMENT ON COLUMN public.experiment_participants.phone_number IS 'Optional contact phone number';
COMMENT ON COLUMN public.experiment_participants.date_of_birth IS 'Date of birth for re-identification';
COMMENT ON COLUMN public.experiment_participants.job_role IS 'Job role type: employee or student';
COMMENT ON COLUMN public.experiment_participants.job_title IS 'Job title (for employees)';
COMMENT ON COLUMN public.experiment_participants.company_name IS 'Company name (for employees)';
COMMENT ON COLUMN public.experiment_participants.field_of_study IS 'Field of study (for students)';
COMMENT ON COLUMN public.experiment_participants.university_name IS 'University name (for students)';
COMMENT ON COLUMN public.experiment_participants.registered_at IS 'Timestamp when participant registered';
COMMENT ON COLUMN public.experiment_participants.onboarding_completed IS 'Whether participant has completed onboarding';

-- ============================================================================
-- 5. EXPERIMENT_TASKS TABLE (Task-Level Performance Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_tasks (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Links
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
    participant_id VARCHAR(36) NOT NULL REFERENCES public.experiment_participants(id) ON DELETE CASCADE,

    -- Task Definition
    task_id VARCHAR(100) NOT NULL,
    task_number INTEGER NOT NULL,

    -- Task Description
    task_description TEXT NOT NULL,
    task_type VARCHAR(50),
    domain VARCHAR(50),
    complexity_level VARCHAR(50),

    -- Success Criteria (Pre-defined)
    expected_insights JSON,
    success_criteria JSON,

    -- Timing (PRIMARY OUTCOME 1: Task Completion Time)
    task_started_at TIMESTAMP WITH TIME ZONE,
    task_completed_at TIMESTAMP WITH TIME ZONE,
    task_duration_seconds INTEGER,

    -- Participant Submission
    submitted_answer TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE,

    -- Answer Quality (PRIMARY OUTCOME 2: Answer Quality)
    answer_completeness_score FLOAT,
    answer_accuracy_score FLOAT,
    answer_depth_score FLOAT,
    overall_answer_quality_score FLOAT,

    -- Process Efficiency (PRIMARY OUTCOME 3: Process Efficiency)
    total_interactions INTEGER DEFAULT 0,
    queries_executed INTEGER DEFAULT 0,
    dashboard_interactions INTEGER DEFAULT 0,
    got_stuck BOOLEAN DEFAULT FALSE,
    gave_up_on_task BOOLEAN DEFAULT FALSE,
    help_requested BOOLEAN DEFAULT FALSE,

    -- Conversational AI Specific (Experimental Group Only)
    chatbot_queries JSON,
    chatbot_query_count INTEGER DEFAULT 0,
    sql_queries_generated JSON,
    visualization_types_used JSON,

    -- Task Outcome
    task_successful BOOLEAN,
    partial_success BOOLEAN DEFAULT FALSE,
    task_abandoned BOOLEAN DEFAULT FALSE,
    abandonment_reason TEXT,

    -- Error Tracking
    errors_encountered JSON,
    technical_issues TEXT,

    -- Participant Feedback (Per-Task)
    task_difficulty_rating INTEGER,
    confidence_in_answer INTEGER,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exp_tasks_experiment ON public.experiment_tasks(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_tasks_participant ON public.experiment_tasks(participant_id);
CREATE INDEX IF NOT EXISTS idx_exp_tasks_task_id ON public.experiment_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_exp_tasks_complexity ON public.experiment_tasks(complexity_level);
CREATE INDEX IF NOT EXISTS idx_tasks_condition_task ON public.experiment_tasks(task_id, participant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_started ON public.experiment_tasks(task_started_at);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON public.experiment_tasks(task_completed_at);

COMMENT ON TABLE public.experiment_tasks IS 'Task-level performance metrics: completion time, answer quality, process efficiency';
COMMENT ON COLUMN public.experiment_tasks.task_duration_seconds IS 'PRIMARY OUTCOME 1: Time from reading task to submitting answer';
COMMENT ON COLUMN public.experiment_tasks.overall_answer_quality_score IS 'PRIMARY OUTCOME 2: Scored on completeness, accuracy, depth';
COMMENT ON COLUMN public.experiment_tasks.total_interactions IS 'PRIMARY OUTCOME 3: Number of steps/interactions needed';
COMMENT ON COLUMN public.experiment_tasks.expected_insights IS 'Pre-defined insights that constitute task success';
COMMENT ON COLUMN public.experiment_tasks.task_type IS 'Examples: simple_lookup, trend_analysis, root_cause_investigation, complex_scenario';

-- ============================================================================
-- 6. QUERY_HISTORY TABLE (Complete Workflow Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.query_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id VARCHAR(36) NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Query Information
    user_query TEXT NOT NULL,
    domain VARCHAR(50),
    is_cross_departmental BOOLEAN DEFAULT FALSE,
    conversation_context JSON,

    -- Orchestrator Output
    orchestrator_action VARCHAR(50),
    orchestrator_reasoning TEXT,
    needs_visualization BOOLEAN DEFAULT FALSE,

    -- Schema Retrieval (RAG)
    retrieved_tables JSON,
    anchor_tables JSON,
    rag_retrieved_tables JSON,
    similarity_scores JSON,
    retrieval_strategy VARCHAR(50),

    -- SQL Generation (with Chain-of-Thought)
    generated_sql TEXT,
    sql_explanation TEXT,
    sql_reasoning_steps JSON,
    tables_used JSON,
    sql_assumptions JSON,
    sql_retry_count INTEGER DEFAULT 0,

    -- SQL Validation
    validation_passed BOOLEAN,
    validation_severity VARCHAR(20),
    validation_issues JSON,
    validation_summary TEXT,

    -- Query Execution
    execution_status VARCHAR(20),
    execution_error TEXT,
    result_data JSON,
    row_count INTEGER,
    execution_time_ms INTEGER,

    -- Multi-Query Iteration
    query_iteration_count INTEGER DEFAULT 0,
    needs_followup_query BOOLEAN DEFAULT FALSE,
    followup_query_reason TEXT,
    all_query_results JSON,

    -- Analysis (Analyst Agent)
    analysis TEXT,
    analysis_reasoning_steps JSON,
    analysis_summary TEXT,
    key_insights JSON,
    recommendations JSON,
    data_quality_notes JSON,

    -- Visualization
    chart_type VARCHAR(50),
    chart_config JSON,
    chart_reasoning TEXT,
    visualization_code TEXT,
    chart_interpretation TEXT,

    -- Token Usage & Cost Tracking
    token_usage JSON,
    total_input_tokens INTEGER,
    total_output_tokens INTEGER,
    total_tokens INTEGER,
    total_cost_usd VARCHAR(20),
    llm_calls_count INTEGER,

    -- Workflow Metadata
    workflow_id VARCHAR(36),
    workflow_started_at TIMESTAMP WITH TIME ZONE,
    workflow_completed_at TIMESTAMP WITH TIME ZONE,
    total_duration_ms INTEGER,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_stage VARCHAR(50),
    error_details TEXT,

    -- Experiment Tracking
    experiment_task_id VARCHAR(36) REFERENCES public.experiment_tasks(id) ON DELETE SET NULL,
    participant_id VARCHAR(36) REFERENCES public.experiment_participants(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_history_user_id ON public.query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_workflow_id ON public.query_history(workflow_id);
CREATE INDEX IF NOT EXISTS idx_query_history_domain ON public.query_history(domain);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON public.query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_total_cost ON public.query_history(total_cost_usd);
CREATE INDEX IF NOT EXISTS idx_query_history_experiment_task ON public.query_history(experiment_task_id);
CREATE INDEX IF NOT EXISTS idx_query_history_participant_id ON public.query_history(participant_id);

COMMENT ON TABLE public.query_history IS 'Complete workflow tracking: queries, SQL, results, visualizations, and all agent outputs';
COMMENT ON COLUMN public.query_history.conversation_context IS 'Compressed conversation history used for context';
COMMENT ON COLUMN public.query_history.sql_reasoning_steps IS 'Chain-of-thought reasoning steps from SQL Agent';
COMMENT ON COLUMN public.query_history.token_usage IS 'Detailed token usage per agent for cost analysis';
COMMENT ON COLUMN public.query_history.workflow_id IS 'Unique ID for tracking complete workflow execution';
COMMENT ON COLUMN public.query_history.all_query_results IS 'Results from all iterations in multi-query scenarios';
COMMENT ON COLUMN public.query_history.experiment_task_id IS 'Links chatbot queries to experiment tasks for experimental group analysis';
COMMENT ON COLUMN public.query_history.participant_id IS 'Direct link to participant for history filtering (multiple participants share same user account)';

-- ============================================================================
-- 7. EXPERIMENT_INTERACTIONS TABLE (Detailed Process Log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_interactions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Links
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
    participant_id VARCHAR(36) NOT NULL REFERENCES public.experiment_participants(id) ON DELETE CASCADE,
    task_id VARCHAR(36) NOT NULL REFERENCES public.experiment_tasks(id) ON DELETE CASCADE,

    -- Interaction Metadata
    interaction_sequence INTEGER NOT NULL,
    interaction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Interaction Type
    interaction_type VARCHAR(50) NOT NULL,

    -- Chatbot Interaction (if applicable)
    user_query TEXT,
    system_response JSON,
    query_understood BOOLEAN,
    query_successful BOOLEAN,

    -- Dashboard Interaction (if applicable)
    dashboard_action VARCHAR(100),
    dashboard_element VARCHAR(100),

    -- Token/Cost Tracking (Experimental Group)
    tokens_used INTEGER,
    cost_usd VARCHAR(20),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exp_interactions_experiment ON public.experiment_interactions(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_interactions_participant ON public.experiment_interactions(participant_id);
CREATE INDEX IF NOT EXISTS idx_exp_interactions_task ON public.experiment_interactions(task_id);
CREATE INDEX IF NOT EXISTS idx_exp_interactions_type ON public.experiment_interactions(interaction_type);

COMMENT ON TABLE public.experiment_interactions IS 'Detailed log of user interactions during task completion (for process efficiency analysis)';

-- ============================================================================
-- 8. RAG TABLE EMBEDDINGS (Vector Storage for Table Retrieval)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rag.table_embeddings (
    id SERIAL PRIMARY KEY,

    -- Table Identification
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) NOT NULL,

    -- Table Metadata
    description TEXT NOT NULL,
    business_terms TEXT[],
    common_questions TEXT[],
    key_columns JSONB,
    sample_values JSONB,
    row_count INTEGER,
    tier INTEGER DEFAULT 1,

    -- Embedding
    embedding_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT unique_table UNIQUE (schema_name, table_name)
);

-- Create IVFFlat index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_table_embeddings_vector
    ON rag.table_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

CREATE INDEX IF NOT EXISTS idx_table_embeddings_tier ON rag.table_embeddings(tier);
CREATE INDEX IF NOT EXISTS idx_table_embeddings_schema ON rag.table_embeddings(schema_name);

COMMENT ON TABLE rag.table_embeddings IS 'Table metadata with vector embeddings for RAG-based table retrieval';
COMMENT ON COLUMN rag.table_embeddings.embedding IS '1536-dimensional embedding from OpenAI text-embedding-3-small';
COMMENT ON COLUMN rag.table_embeddings.tier IS '1=Core tables (always considered), 2=Important tables (secondary)';
COMMENT ON COLUMN rag.table_embeddings.key_columns IS 'JSON object mapping column names to descriptions';
COMMENT ON COLUMN rag.table_embeddings.business_terms IS 'Array of business terms related to this table';
COMMENT ON COLUMN rag.table_embeddings.common_questions IS 'Array of common questions this table can answer';

-- ============================================================================
-- 9. INSERT DEFAULT EXPERIMENT
-- ============================================================================
INSERT INTO public.experiments (
    id,
    name,
    description,
    research_question,
    hypothesis,
    study_type,
    design_type,
    control_condition_name,
    experimental_condition_name,
    control_description,
    experimental_description,
    target_participants_per_group,
    llm_model,
    status
) VALUES (
    'default-experiment-001',
    'NL2SQL Conversational AI User Study',
    'Between-subjects study comparing traditional BI dashboard usage vs. dashboard + conversational AI chatbot for business data analysis',
    'Does integrating a conversational AI chatbot with traditional BI dashboards improve decision-making quality, task completion time, and process efficiency for business users?',
    'Users with access to the conversational AI chatbot will demonstrate: (1) faster task completion times, (2) higher quality analytical insights, and (3) more efficient exploration processes compared to users with only traditional dashboard access.',
    'user_study',
    'between_subjects',
    'BI Dashboard (Control)',
    'Dashboard + Conversational AI (Experimental)',
    'Traditional BI dashboard with pre-built visualizations, filtering capabilities, drill-down functionality, and complete documentation',
    'Same BI dashboard plus integrated conversational chatbot with natural language queries, SQL explanations, and contextual data interpretations',
    15,
    'claude-sonnet-4-5',
    'active'
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 10. INSERT DEFAULT USERS (for experiment)
-- ============================================================================
-- Note: Password is 'password123' hashed with bcrypt
-- You should change these passwords in production!

-- Admin user
INSERT INTO public.users (id, email, password_hash, full_name, is_active, is_admin, role)
VALUES (
    'admin-user-001',
    'admin@thesis.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4i.P5OHmYrJHrGHC',
    'Admin User',
    TRUE,
    TRUE,
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Control group user (shared account for control participants)
INSERT INTO public.users (id, email, password_hash, full_name, is_active, is_admin, role)
VALUES (
    'control-user-001',
    'user1@thesis.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4i.P5OHmYrJHrGHC',
    'Control Group User',
    TRUE,
    FALSE,
    'participant_control'
) ON CONFLICT (email) DO NOTHING;

-- Experimental group user (shared account for experimental participants)
INSERT INTO public.users (id, email, password_hash, full_name, is_active, is_admin, role)
VALUES (
    'experimental-user-001',
    'user2@thesis.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4i.P5OHmYrJHrGHC',
    'Experimental Group User',
    TRUE,
    FALSE,
    'participant_experimental'
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the setup was successful:

-- Check all tables created
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('public', 'rag')
ORDER BY schemaname, tablename;

-- Check pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Check users created
SELECT id, email, role, is_admin FROM public.users;

-- Check experiment created
SELECT id, name, status FROM public.experiments;

-- ============================================================================
-- END OF SETUP SCRIPT
-- ============================================================================
