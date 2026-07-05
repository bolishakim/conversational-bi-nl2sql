-- Migration 010: Backfill experiment_interactions for historical chatbot queries
--
-- Companion to migration 009. The counter fix in 009 updated
-- experiment_tasks.chatbot_query_count but did not write rows into the
-- fine-grained experiment_interactions log, so the admin per-participant
-- timeline still shows no chatbot activity for pre-fix participants.
--
-- This migration inserts one ExperimentInteraction row per pre-fix
-- query_history row that can be attributed to a task window, with
-- interaction_type='chatbot_query'. Sequence numbers are appended after
-- any existing rows for the task.
--
-- Idempotency: only runs for participants who currently have zero
-- chatbot_query rows in experiment_interactions. Running again is a no-op.
--
-- Safe to run on production. Does not delete or modify existing data.

BEGIN;

WITH
-- query_history rows that fall inside an active task window for the same participant
attributed AS (
    SELECT
        qh.id               AS query_id,
        qh.participant_id,
        qh.created_at,
        qh.user_query,
        qh.execution_status,
        qh.error_stage,
        qh.total_tokens,
        qh.total_cost_usd,
        qh.generated_sql,
        qh.row_count,
        qh.chart_type,
        et.id               AS task_db_id,
        et.experiment_id
    FROM public.query_history qh
    JOIN public.experiment_tasks et
      ON et.participant_id = qh.participant_id
     AND qh.created_at >= et.task_started_at
     AND (et.task_completed_at IS NULL OR qh.created_at < et.task_completed_at)
    WHERE qh.participant_id IS NOT NULL
),
-- Guard: only backfill participants who currently have zero chatbot_query interactions
to_backfill AS (
    SELECT a.*
    FROM attributed a
    WHERE a.participant_id NOT IN (
        SELECT DISTINCT participant_id
        FROM public.experiment_interactions
        WHERE interaction_type = 'chatbot_query'
    )
),
-- Per-task sequence ordering starting after the existing max
numbered AS (
    SELECT
        b.*,
        ROW_NUMBER() OVER (PARTITION BY b.task_db_id ORDER BY b.created_at) AS rn_in_task,
        COALESCE(
            (SELECT MAX(interaction_sequence)
               FROM public.experiment_interactions
              WHERE task_id = b.task_db_id),
            0
        ) AS existing_max
    FROM to_backfill b
)
INSERT INTO public.experiment_interactions (
    id, experiment_id, participant_id, task_id,
    interaction_sequence, interaction_timestamp,
    interaction_type, user_query, system_response,
    query_understood, query_successful,
    tokens_used, cost_usd, created_at
)
SELECT
    gen_random_uuid()::text,
    experiment_id,
    participant_id,
    task_db_id,
    existing_max + rn_in_task,
    created_at,
    'chatbot_query',
    user_query,
    jsonb_build_object(
        'execution_status', execution_status,
        'row_count', row_count,
        'chart_type', chart_type,
        'sql', LEFT(COALESCE(generated_sql, ''), 500)
    ),
    (error_stage IS NULL OR error_stage <> 'orchestrator'),
    (execution_status = 'success'),
    total_tokens,
    CASE WHEN total_cost_usd IS NOT NULL THEN total_cost_usd::text ELSE NULL END,
    created_at
FROM numbered;

COMMIT;
