-- Migration: Add Pre-Survey Fields (Replace PII with Anonymous Data)
-- Date: 2025-01-13
-- Purpose: Support new onboarding flow with 7 anonymous pre-survey questions
--          No personally identifiable information (PII) is collected

-- ============================================================================
-- ADD PRE-SURVEY FIELDS TO EXPERIMENT_PARTICIPANTS
-- ============================================================================

-- Q1: Age Range (replaces collecting exact DOB)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS age_range VARCHAR(50);
COMMENT ON COLUMN public.experiment_participants.age_range IS 'Age range: 18-24, 25-34, 35-44, 45-54, 55+';

-- Q2: Occupation Status (replaces job_role with more options)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS occupation_status VARCHAR(50);
COMMENT ON COLUMN public.experiment_participants.occupation_status IS 'Occupation status: student, employee, self_employed, other';

-- Q3: Field of Work/Study (more general than field_of_study)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS field_of_work VARCHAR(100);
COMMENT ON COLUMN public.experiment_participants.field_of_work IS 'Field of work/study: business, computer_science, engineering, natural_sciences, social_sciences, other';

-- Q4: Visual Analytics Frequency
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS visual_analytics_frequency VARCHAR(50);
COMMENT ON COLUMN public.experiment_participants.visual_analytics_frequency IS 'How often works with visual data analytics: never, rarely, occasionally, regularly, daily';

-- Q5: Business Background
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS business_background VARCHAR(100);
COMMENT ON COLUMN public.experiment_participants.business_background IS 'Business background: education, experience, both, none';

-- Q6: LLM Chatbot Experience
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS llm_chatbot_experience VARCHAR(50);
COMMENT ON COLUMN public.experiment_participants.llm_chatbot_experience IS 'LLM chatbot experience: never, once_twice, occasionally, regularly';

-- Q7: BI Tools Experience (already exists but adding comment for clarity)
-- Note: bi_tools_experience column already exists from original schema
COMMENT ON COLUMN public.experiment_participants.bi_tools_experience IS 'BI tools experience: none, minimal, basic, intermediate, advanced';

-- ============================================================================
-- MARK LEGACY FIELDS (kept for backward compatibility, no longer collected)
-- ============================================================================

-- The following fields are no longer collected in the new onboarding flow:
-- - full_name (PII - removed)
-- - phone_number (PII - removed)
-- - date_of_birth (PII - replaced with age_range)
-- - job_role (replaced with occupation_status)
-- - job_title (PII - removed)
-- - company_name (PII - removed)
-- - field_of_study (merged into field_of_work)
-- - university_name (PII - removed)
-- - email_hash (no longer needed)
-- - gender (no longer collected)
-- - education_level (no longer collected)
-- - occupation (replaced with occupation_status)
-- - industry (no longer collected)
-- - sql_proficiency (no longer collected)
-- - data_analysis_experience_years (no longer collected)

-- Add comments to legacy fields to indicate they are deprecated
COMMENT ON COLUMN public.experiment_participants.full_name IS 'DEPRECATED: No longer collected (PII)';
COMMENT ON COLUMN public.experiment_participants.phone_number IS 'DEPRECATED: No longer collected (PII)';
COMMENT ON COLUMN public.experiment_participants.date_of_birth IS 'DEPRECATED: Replaced by age_range (PII)';
COMMENT ON COLUMN public.experiment_participants.job_role IS 'DEPRECATED: Replaced by occupation_status';
COMMENT ON COLUMN public.experiment_participants.job_title IS 'DEPRECATED: No longer collected (PII)';
COMMENT ON COLUMN public.experiment_participants.company_name IS 'DEPRECATED: No longer collected (PII)';
COMMENT ON COLUMN public.experiment_participants.field_of_study IS 'DEPRECATED: Merged into field_of_work';
COMMENT ON COLUMN public.experiment_participants.university_name IS 'DEPRECATED: No longer collected (PII)';

-- ============================================================================
-- CREATE INDEX FOR NEW LOOKUP METHOD
-- ============================================================================

-- Since we no longer collect name/DOB, returning participants are identified by code only
CREATE INDEX IF NOT EXISTS idx_exp_participants_code ON public.experiment_participants(participant_code);

-- ============================================================================
-- VERIFICATION QUERY (run manually to verify migration)
-- ============================================================================
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'experiment_participants'
-- ORDER BY ordinal_position;
