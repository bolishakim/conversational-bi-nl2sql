-- Migration: Extend QueryHistory table for full workflow persistence
-- Date: 2025-12-13
-- Purpose: Add comprehensive tracking for thesis analysis

-- Add new columns to query_history table
ALTER TABLE public.query_history

-- Query Information
ADD COLUMN IF NOT EXISTS is_cross_departmental BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS conversation_context JSON,

-- Orchestrator Output
ADD COLUMN IF NOT EXISTS orchestrator_action VARCHAR(50),
ADD COLUMN IF NOT EXISTS orchestrator_reasoning TEXT,
ADD COLUMN IF NOT EXISTS needs_visualization BOOLEAN DEFAULT FALSE,

-- Schema Retrieval (RAG)
ADD COLUMN IF NOT EXISTS rag_retrieved_tables JSON,
ADD COLUMN IF NOT EXISTS retrieval_strategy VARCHAR(50),

-- SQL Generation (with Chain-of-Thought)
ADD COLUMN IF NOT EXISTS sql_reasoning_steps JSON,
ADD COLUMN IF NOT EXISTS tables_used JSON,
ADD COLUMN IF NOT EXISTS sql_assumptions JSON,
ADD COLUMN IF NOT EXISTS sql_retry_count INTEGER DEFAULT 0,

-- SQL Validation
ADD COLUMN IF NOT EXISTS validation_passed BOOLEAN,
ADD COLUMN IF NOT EXISTS validation_severity VARCHAR(20),
ADD COLUMN IF NOT EXISTS validation_issues JSON,
ADD COLUMN IF NOT EXISTS validation_summary TEXT,

-- Multi-Query Iteration
ADD COLUMN IF NOT EXISTS query_iteration_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS needs_followup_query BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS followup_query_reason TEXT,
ADD COLUMN IF NOT EXISTS all_query_results JSON,

-- Analysis (Analyst Agent)
ADD COLUMN IF NOT EXISTS analysis_reasoning_steps JSON,
ADD COLUMN IF NOT EXISTS analysis_summary TEXT,
ADD COLUMN IF NOT EXISTS key_insights JSON,
ADD COLUMN IF NOT EXISTS recommendations JSON,
ADD COLUMN IF NOT EXISTS data_quality_notes JSON,

-- Visualization
ADD COLUMN IF NOT EXISTS chart_reasoning TEXT,
ADD COLUMN IF NOT EXISTS visualization_code TEXT,

-- Token Usage & Cost Tracking
ADD COLUMN IF NOT EXISTS token_usage JSON,
ADD COLUMN IF NOT EXISTS total_input_tokens INTEGER,
ADD COLUMN IF NOT EXISTS total_output_tokens INTEGER,
ADD COLUMN IF NOT EXISTS total_tokens INTEGER,
ADD COLUMN IF NOT EXISTS total_cost_usd VARCHAR(20),
ADD COLUMN IF NOT EXISTS llm_calls_count INTEGER,

-- Workflow Metadata
ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(36),
ADD COLUMN IF NOT EXISTS workflow_started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS workflow_completed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS total_duration_ms INTEGER,
ADD COLUMN IF NOT EXISTS error_occurred BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS error_stage VARCHAR(50),
ADD COLUMN IF NOT EXISTS error_details TEXT;

-- Create indexes for thesis analysis queries
CREATE INDEX IF NOT EXISTS idx_query_history_workflow_id ON public.query_history(workflow_id);
CREATE INDEX IF NOT EXISTS idx_query_history_domain ON public.query_history(domain);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON public.query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_total_cost ON public.query_history(total_cost_usd);

-- Add comments for documentation
COMMENT ON COLUMN public.query_history.conversation_context IS 'Compressed conversation history used for context';
COMMENT ON COLUMN public.query_history.sql_reasoning_steps IS 'Chain-of-thought reasoning steps from SQL Agent';
COMMENT ON COLUMN public.query_history.token_usage IS 'Detailed token usage per agent for cost analysis';
COMMENT ON COLUMN public.query_history.workflow_id IS 'Unique ID for tracking complete workflow execution';
COMMENT ON COLUMN public.query_history.all_query_results IS 'Results from all iterations in multi-query scenarios';
