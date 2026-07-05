-- Migration 007: Update pre-survey fields
-- 1. Add exact age column (replaces age_range)
-- 2. Add occupation_statuses column for multi-select (replaces occupation_status)
-- 3. Add field_of_study column for conditional field when student is selected

ALTER TABLE experiment_participants ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE experiment_participants ADD COLUMN IF NOT EXISTS occupation_statuses VARCHAR(200);
ALTER TABLE experiment_participants ADD COLUMN IF NOT EXISTS field_of_study VARCHAR(100);
