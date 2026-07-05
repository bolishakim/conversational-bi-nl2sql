-- Migration: Add participant_id to Query History
-- Date: 2025-01-03
-- Purpose: Support filtering query history by participant for shared user accounts
--          Multiple participants use the same user account (user1 or user2) sequentially,
--          so we need to track which participant made each query.

-- ============================================================================
-- ADD PARTICIPANT_ID TO QUERY_HISTORY
-- ============================================================================

-- Add participant_id column with foreign key reference
ALTER TABLE public.query_history
ADD COLUMN IF NOT EXISTS participant_id VARCHAR(36) REFERENCES public.experiment_participants(id) ON DELETE SET NULL;

-- Create index for faster lookups by participant
CREATE INDEX IF NOT EXISTS idx_query_history_participant_id ON public.query_history(participant_id);

-- Comments
COMMENT ON COLUMN public.query_history.participant_id IS 'Direct link to participant for history filtering (multiple participants share same user account)';
