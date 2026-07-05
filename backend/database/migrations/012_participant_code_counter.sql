-- Migration 012: monotonic per-experiment participant code counter
--
-- Old behavior: generate_participant_code used COUNT(*) of existing rows + 1.
-- That reused codes after deletions and could collide with codes already
-- assigned to participants whose rows were later removed (e.g. the buggy
-- April 2026 Prolific batch). The new column persists the high-water mark
-- per experiment and is incremented atomically on each registration, so a
-- code is never reused.

ALTER TABLE public.experiments
  ADD COLUMN IF NOT EXISTS next_participant_number INTEGER NOT NULL DEFAULT 1;

-- Initialize the counter from the current MAX numeric suffix per experiment,
-- so existing data is preserved and the next code follows it.
UPDATE public.experiments e
SET next_participant_number = sub.next_num
FROM (
  SELECT
    experiment_id,
    COALESCE(MAX(NULLIF(SUBSTRING(participant_code FROM 2), '')::int), 0) + 1 AS next_num
  FROM public.experiment_participants
  GROUP BY experiment_id
) sub
WHERE e.id = sub.experiment_id;
