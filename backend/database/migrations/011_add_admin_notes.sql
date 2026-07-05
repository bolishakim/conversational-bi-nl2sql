-- Migration 011: Admin audit-trail column for manual participant actions
--
-- Adds a free-text `admin_notes` column on experiment_participants. The admin
-- UI appends timestamped lines to it when a researcher excludes, withdraws,
-- reassigns, or reinstates a participant. Keeps a compact human-readable
-- history without needing a separate audit table.

ALTER TABLE public.experiment_participants
    ADD COLUMN IF NOT EXISTS admin_notes TEXT;
