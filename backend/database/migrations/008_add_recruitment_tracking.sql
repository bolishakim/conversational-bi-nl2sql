-- Migration 008: Add recruitment-source tracking for Prolific launch
-- Adds columns to distinguish university-recruited vs Prolific-recruited
-- participants, and to persist Prolific PID / STUDY_ID / SESSION_ID when
-- present in the registration URL.

-- 1. recruitment_source: 'university' for existing rows, 'prolific' for new
--    Prolific-originated rows. Default 'university' on ADD COLUMN so the
--    13 pre-existing participants are correctly tagged without a separate
--    UPDATE step.
ALTER TABLE public.experiment_participants
    ADD COLUMN IF NOT EXISTS recruitment_source VARCHAR(20)
        DEFAULT 'university'
        CHECK (recruitment_source IN ('university', 'prolific'));

-- 2. Prolific identifiers (all nullable; populated only when participant
--    arrives from a Prolific URL with these query params)
ALTER TABLE public.experiment_participants
    ADD COLUMN IF NOT EXISTS prolific_pid VARCHAR(100);

ALTER TABLE public.experiment_participants
    ADD COLUMN IF NOT EXISTS prolific_study_id VARCHAR(100);

ALTER TABLE public.experiment_participants
    ADD COLUMN IF NOT EXISTS prolific_session_id VARCHAR(100);

-- 3. Partial unique index on prolific_pid: enforces one participant row per
--    Prolific submission while still allowing many NULLs (university rows).
CREATE UNIQUE INDEX IF NOT EXISTS idx_experiment_participants_prolific_pid
    ON public.experiment_participants (prolific_pid)
    WHERE prolific_pid IS NOT NULL;

-- 4. Index for filtering the admin participant list by source
CREATE INDEX IF NOT EXISTS idx_experiment_participants_recruitment_source
    ON public.experiment_participants (recruitment_source);
