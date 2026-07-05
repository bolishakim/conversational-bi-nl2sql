-- Migration: Add Participant Onboarding Fields
-- Date: 2025-12-27
-- Purpose: Support participant registration flow with minimal personal data for academic research

-- ============================================================================
-- ADD ONBOARDING FIELDS TO EXPERIMENT_PARTICIPANTS
-- ============================================================================

-- Full name (for identification)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);

-- Phone number (optional contact)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50);

-- Date of birth (for re-identification and age verification)
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS date_of_birth DATE;

-- Job role details
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS job_role VARCHAR(100); -- 'employee' or 'student'
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS job_title VARCHAR(255); -- Job title for employees
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS company_name VARCHAR(255); -- Company name for employees
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS field_of_study VARCHAR(255); -- Field of study for students
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS university_name VARCHAR(255); -- University name for students

-- Registration tracking
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.experiment_participants ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;

-- Create index for lookup by name + DOB (for returning participants)
CREATE INDEX IF NOT EXISTS idx_exp_participants_name_dob ON public.experiment_participants(full_name, date_of_birth);

-- Comments
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
