-- ============================================================================
-- Migration 006: Add Tutorial Fields to Experiment Tasks
-- ============================================================================
-- Adds support for marking tasks as tutorial with step-by-step guides
-- Date: 2026-02-11
-- ============================================================================

-- Add tutorial fields to experiment_tasks table
ALTER TABLE public.experiment_tasks
ADD COLUMN IF NOT EXISTS is_tutorial BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS tutorial_steps TEXT,
ADD COLUMN IF NOT EXISTS tutorial_tips TEXT;

-- Add comment for documentation
COMMENT ON COLUMN public.experiment_tasks.is_tutorial IS 'Indicates if this task is a tutorial task (not analyzed in results)';
COMMENT ON COLUMN public.experiment_tasks.tutorial_steps IS 'Step-by-step guide for tutorial tasks (shown to all participants)';
COMMENT ON COLUMN public.experiment_tasks.tutorial_tips IS 'Additional tips for completing tutorial tasks';

-- Verify the migration
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'experiment_tasks'
  AND column_name IN ('is_tutorial', 'tutorial_steps', 'tutorial_tips');
