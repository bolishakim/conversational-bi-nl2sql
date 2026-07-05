-- Migration: Create Experiment Schema for User Study
-- Date: 2025-12-13
-- Purpose: Support between-subjects user study comparing BI dashboard (control) vs. conversational AI (experimental)
-- Study Design: Measure decision-making quality, task completion time, and process efficiency

-- ============================================================================
-- 0. EXTEND USERS TABLE WITH ROLE
-- ============================================================================
-- Add role column to users table for experiment access control
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'participant_control';

-- Create index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);

COMMENT ON COLUMN public.users.role IS 'User role: admin, participant_control (dashboard only), participant_experimental (dashboard + chatbot)';

-- ============================================================================
-- 1. EXPERIMENTS TABLE (Study-Level Metadata)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiments (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Experiment Information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    research_question TEXT,
    hypothesis TEXT,

    -- Study Design (Between-Subjects)
    study_type VARCHAR(50) DEFAULT 'user_study', -- 'user_study', 'pilot', 'field_study'
    design_type VARCHAR(50) DEFAULT 'between_subjects', -- Fixed for this thesis

    -- Experimental Conditions
    control_condition_name VARCHAR(100) DEFAULT 'BI Dashboard (Control)',
    experimental_condition_name VARCHAR(100) DEFAULT 'Dashboard + Conversational AI (Experimental)',
    control_description TEXT, -- "Traditional BI dashboard with pre-built visualizations"
    experimental_description TEXT, -- "Same dashboard + integrated conversational chatbot"

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
    target_participants_per_group INTEGER DEFAULT 15, -- Aiming for 20-30 total (10-15 per group)
    actual_control_participants INTEGER DEFAULT 0,
    actual_experimental_participants INTEGER DEFAULT 0,

    -- System Configuration (for reproducibility)
    system_version VARCHAR(50),
    llm_model VARCHAR(100), -- 'claude-sonnet-4-5'
    optimization_settings JSON, -- TOP_K_TABLES, prompts version, etc.

    -- Task Design
    total_tasks INTEGER, -- Number of analytical tasks
    task_definitions JSON, -- Array of task objects with success criteria

    -- Status
    status VARCHAR(50) DEFAULT 'planning', -- 'planning', 'recruiting', 'active', 'completed', 'cancelled'

    -- Metadata
    created_by VARCHAR(36) REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_experiments_status ON public.experiments(status);
CREATE INDEX idx_experiments_dates ON public.experiments(actual_start_date, actual_end_date);

COMMENT ON TABLE public.experiments IS 'Study-level metadata for between-subjects user experiments';


-- ============================================================================
-- 2. EXPERIMENT_PARTICIPANTS TABLE (Participant Demographics & Assignment)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_participants (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Link to Experiment
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,

    -- Participant Identification (Anonymized)
    participant_code VARCHAR(100) UNIQUE NOT NULL, -- 'P001', 'P002', etc.
    user_id VARCHAR(36) REFERENCES public.users(id) ON DELETE SET NULL, -- System user account

    -- Demographics (collected for analysis)
    age_group VARCHAR(50), -- '18-24', '25-34', '35-44', '45-54', '55+'
    gender VARCHAR(50), -- Optional
    education_level VARCHAR(100), -- 'Bachelor', 'Master', 'PhD', etc.
    occupation VARCHAR(100),
    industry VARCHAR(100), -- 'Technology', 'Finance', 'Healthcare', etc.

    -- Technical Background
    sql_proficiency VARCHAR(50), -- 'none', 'basic', 'intermediate', 'advanced', 'expert'
    bi_tools_experience VARCHAR(50), -- 'none', 'basic', 'intermediate', 'advanced', 'expert'
    data_analysis_experience_years INTEGER, -- Years of experience

    -- Contact (encrypted/hashed for privacy)
    email_hash VARCHAR(255), -- SHA-256 hash for re-contact if needed

    -- Consent & Privacy
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    data_retention_until DATE, -- When to delete PII
    withdrawal_requested BOOLEAN DEFAULT FALSE,
    withdrawal_timestamp TIMESTAMP WITH TIME ZONE,

    -- Experimental Assignment (Between-Subjects)
    condition_assigned VARCHAR(50) NOT NULL, -- 'control' or 'experimental'
    assignment_method VARCHAR(50) DEFAULT 'random', -- 'random', 'stratified', 'manual'
    randomization_seed INTEGER, -- For reproducibility
    assignment_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Pre-Study Baseline
    baseline_survey_responses JSON, -- Pre-study questionnaire responses
    baseline_technical_test_score FLOAT, -- Optional: SQL/BI proficiency test

    -- Post-Study Measures
    post_study_survey_responses JSON, -- Comprehensive post-study questionnaire

    -- Usability Metrics (Experimental Group)
    system_usability_scale_score FLOAT, -- SUS score (0-100)
    chatbot_understanding_rating INTEGER, -- 1-5: Did chatbot understand questions?
    explanation_helpfulness_rating INTEGER, -- 1-5: Were explanations helpful?
    sql_trust_rating INTEGER, -- 1-5: Did you trust generated SQL?
    overall_satisfaction_rating INTEGER, -- 1-5: Overall satisfaction
    would_use_at_work BOOLEAN, -- Would you use this at work?

    -- User Experience Metrics
    perceived_usefulness INTEGER, -- 1-5 Likert
    perceived_ease_of_use INTEGER, -- 1-5 Likert
    frustration_level INTEGER, -- 1-5 Likert (1=none, 5=very frustrated)
    confidence_in_results INTEGER, -- 1-5 Likert

    -- Completion Status
    session_completed BOOLEAN DEFAULT FALSE,
    session_completed_at TIMESTAMP WITH TIME ZONE,
    tasks_completed INTEGER DEFAULT 0,
    tasks_attempted INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'recruited', -- 'recruited', 'active', 'completed', 'withdrawn', 'excluded'
    exclusion_reason TEXT, -- If excluded from analysis

    -- Metadata
    recruited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    first_task_at TIMESTAMP WITH TIME ZONE,
    last_task_at TIMESTAMP WITH TIME ZONE,
    total_session_duration_minutes INTEGER,

    notes TEXT
);

CREATE INDEX idx_exp_participants_experiment ON public.experiment_participants(experiment_id);
CREATE INDEX idx_exp_participants_code ON public.experiment_participants(participant_code);
CREATE INDEX idx_exp_participants_condition ON public.experiment_participants(condition_assigned);
CREATE INDEX idx_exp_participants_status ON public.experiment_participants(status);

COMMENT ON TABLE public.experiment_participants IS 'Participant demographics and experimental condition assignment';
COMMENT ON COLUMN public.experiment_participants.condition_assigned IS 'Between-subjects assignment: control or experimental';


-- ============================================================================
-- 3. EXPERIMENT_TASKS TABLE (Task-Level Performance Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_tasks (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Links
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
    participant_id VARCHAR(36) NOT NULL REFERENCES public.experiment_participants(id) ON DELETE CASCADE,
    query_history_id VARCHAR(36) REFERENCES public.query_history(id) ON DELETE SET NULL, -- Only for experimental group

    -- Task Definition
    task_id VARCHAR(100) NOT NULL, -- 'T001', 'T002', etc.
    task_number INTEGER NOT NULL, -- Order presented (1, 2, 3...)

    -- Task Description
    task_description TEXT NOT NULL, -- Business scenario: "Identify top 3 product categories by revenue..."
    task_type VARCHAR(50), -- 'simple_lookup', 'trend_analysis', 'root_cause_investigation', 'complex_scenario'
    domain VARCHAR(50), -- 'sales', 'hr', 'production', 'cross_domain'
    complexity_level VARCHAR(50), -- 'easy', 'medium', 'hard'

    -- Success Criteria (Pre-defined)
    expected_insights JSON, -- List of key insights participant should discover
    success_criteria JSON, -- How to judge if task was completed correctly

    -- Timing (PRIMARY OUTCOME 1: Task Completion Time)
    task_started_at TIMESTAMP WITH TIME ZONE,
    task_completed_at TIMESTAMP WITH TIME ZONE,
    task_duration_seconds INTEGER, -- How long from reading task to submitting answer

    -- Participant Submission
    submitted_answer TEXT, -- Natural language answer/recommendation submitted
    submitted_at TIMESTAMP WITH TIME ZONE,

    -- Answer Quality (PRIMARY OUTCOME 2: Answer Quality)
    answer_completeness_score FLOAT, -- 0-1: Did they find all key insights?
    answer_accuracy_score FLOAT, -- 0-1: Were insights correct?
    answer_depth_score FLOAT, -- 0-1: Quality of explanation/reasoning
    overall_answer_quality_score FLOAT, -- 0-1: Weighted average or holistic score

    -- Process Efficiency (PRIMARY OUTCOME 3: Process Efficiency)
    total_interactions INTEGER DEFAULT 0, -- Number of clicks/queries/filters used
    queries_executed INTEGER DEFAULT 0, -- For experimental: number of chatbot queries
    dashboard_interactions INTEGER DEFAULT 0, -- Number of dashboard clicks/filters
    got_stuck BOOLEAN DEFAULT FALSE, -- Did participant get stuck?
    gave_up_on_task BOOLEAN DEFAULT FALSE, -- Did they abandon the task?
    help_requested BOOLEAN DEFAULT FALSE, -- Did they ask researcher for help?

    -- Conversational AI Specific (Experimental Group Only)
    chatbot_queries JSON, -- Array of natural language queries to chatbot
    chatbot_query_count INTEGER DEFAULT 0,
    sql_queries_generated JSON, -- Array of SQL queries generated by system
    visualization_types_used JSON, -- Array of chart types viewed

    -- Task Outcome
    task_successful BOOLEAN, -- Did they meet success criteria?
    partial_success BOOLEAN DEFAULT FALSE, -- Found some but not all insights
    task_abandoned BOOLEAN DEFAULT FALSE,
    abandonment_reason TEXT,

    -- Error Tracking
    errors_encountered JSON, -- Any errors or issues during task
    technical_issues TEXT,

    -- Participant Feedback (Per-Task)
    task_difficulty_rating INTEGER, -- 1-5: How difficult did you find this task?
    confidence_in_answer INTEGER, -- 1-5: How confident are you in your answer?

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_exp_tasks_experiment ON public.experiment_tasks(experiment_id);
CREATE INDEX idx_exp_tasks_participant ON public.experiment_tasks(participant_id);
CREATE INDEX idx_exp_tasks_query_history ON public.experiment_tasks(query_history_id);
CREATE INDEX idx_exp_tasks_task_id ON public.experiment_tasks(task_id);
CREATE INDEX idx_exp_tasks_complexity ON public.experiment_tasks(complexity_level);

COMMENT ON TABLE public.experiment_tasks IS 'Task-level performance metrics: completion time, answer quality, process efficiency';
COMMENT ON COLUMN public.experiment_tasks.task_duration_seconds IS 'PRIMARY OUTCOME 1: Time from reading task to submitting answer';
COMMENT ON COLUMN public.experiment_tasks.overall_answer_quality_score IS 'PRIMARY OUTCOME 2: Scored on completeness, accuracy, depth';
COMMENT ON COLUMN public.experiment_tasks.total_interactions IS 'PRIMARY OUTCOME 3: Number of steps/interactions needed';


-- ============================================================================
-- 4. EXPERIMENT_INTERACTIONS TABLE (Detailed Process Log - Experimental Group)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_interactions (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,

    -- Links
    experiment_id VARCHAR(36) NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
    participant_id VARCHAR(36) NOT NULL REFERENCES public.experiment_participants(id) ON DELETE CASCADE,
    task_id VARCHAR(36) NOT NULL REFERENCES public.experiment_tasks(id) ON DELETE CASCADE,

    -- Interaction Metadata
    interaction_sequence INTEGER NOT NULL, -- Order within task (1, 2, 3...)
    interaction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Interaction Type
    interaction_type VARCHAR(50) NOT NULL, -- 'chatbot_query', 'dashboard_filter', 'visualization_view', 'data_export', 'help_request'

    -- Chatbot Interaction (if applicable)
    user_query TEXT, -- Natural language query to chatbot
    system_response JSON, -- Full chatbot response (SQL, explanation, chart, etc.)
    query_understood BOOLEAN, -- Did chatbot understand the query?
    query_successful BOOLEAN, -- Did query execute successfully?

    -- Dashboard Interaction (if applicable)
    dashboard_action VARCHAR(100), -- 'filter_sales', 'drill_down_product', 'view_chart', etc.
    dashboard_element VARCHAR(100), -- Which dashboard component

    -- Token/Cost Tracking (Experimental Group)
    tokens_used INTEGER,
    cost_usd VARCHAR(20),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_exp_interactions_experiment ON public.experiment_interactions(experiment_id);
CREATE INDEX idx_exp_interactions_participant ON public.experiment_interactions(participant_id);
CREATE INDEX idx_exp_interactions_task ON public.experiment_interactions(task_id);
CREATE INDEX idx_exp_interactions_type ON public.experiment_interactions(interaction_type);

COMMENT ON TABLE public.experiment_interactions IS 'Detailed log of user interactions during task completion (for process efficiency analysis)';


-- ============================================================================
-- Add indexes for common analysis queries
-- ============================================================================

-- Compare control vs experimental groups
CREATE INDEX idx_participants_condition_status ON public.experiment_participants(condition_assigned, status);

-- Task performance analysis
CREATE INDEX idx_tasks_condition_task ON public.experiment_tasks(task_id, participant_id);

-- Time-based analysis
CREATE INDEX idx_tasks_started ON public.experiment_tasks(task_started_at);
CREATE INDEX idx_tasks_completed ON public.experiment_tasks(task_completed_at);


-- ============================================================================
-- Database information
-- ============================================================================

COMMENT ON COLUMN public.experiments.control_description IS 'Traditional BI dashboard with pre-built visualizations, filtering, drill-down, complete documentation';
COMMENT ON COLUMN public.experiments.experimental_description IS 'Same BI dashboard + integrated conversational chatbot with NL queries, SQL explanations, contextual interpretations';

COMMENT ON COLUMN public.experiment_participants.sql_proficiency IS 'Varying levels intentional: system meant for both data analysts and business users';
COMMENT ON COLUMN public.experiment_participants.condition_assigned IS 'Between-subjects: each participant sees ONLY control OR experimental condition';

COMMENT ON COLUMN public.experiment_tasks.expected_insights IS 'Pre-defined insights that constitute task success (e.g., "Q3 dip caused by staffing changes in Territory X")';
COMMENT ON COLUMN public.experiment_tasks.task_type IS 'Examples: simple_lookup="Find top 3 categories", complex_scenario="Investigate Q3 performance dip"';


-- ============================================================================
-- 5. LINK QUERY_HISTORY TO EXPERIMENT SESSIONS (for experimental group)
-- ============================================================================
-- Add experiment_session_id to query_history for linking chatbot queries to experiment tasks
ALTER TABLE public.query_history ADD COLUMN IF NOT EXISTS experiment_task_id VARCHAR(36) REFERENCES public.experiment_tasks(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_query_history_experiment_task ON public.query_history(experiment_task_id);

COMMENT ON COLUMN public.query_history.experiment_task_id IS 'Links chatbot queries to experiment tasks for experimental group analysis';
