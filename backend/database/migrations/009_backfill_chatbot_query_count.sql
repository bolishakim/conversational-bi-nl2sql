-- Migration 009: One-off data fix -- backfill chatbot_query_count from query_history
--
-- Background: before the fix in chat.py, chatbot queries were persisted to
-- query_history but never triggered log_chatbot_query, so
-- experiment_tasks.chatbot_query_count (and queries_executed, total_interactions)
-- stayed at 0 even for experimental participants who clearly used the chatbot
-- (P002=6, P005=4, P006=3, P013=3 queries in query_history).
--
-- This migration attributes each query_history row to the experiment task
-- that was active at the time the query was made (task_started_at <= created_at
-- < task_completed_at) and updates the three counters accordingly.
--
-- Idempotency: only touches tasks where chatbot_query_count is still 0, so
-- re-running does not double-count after new queries land via the fixed path.
--
-- Safe to run on a production database. Does not delete any data.

BEGIN;

WITH per_task_chatbot AS (
    SELECT
        et.id AS task_db_id,
        COUNT(qh.id) AS chatbot_count
    FROM public.experiment_tasks et
    LEFT JOIN public.query_history qh
        ON qh.participant_id = et.participant_id
        AND qh.created_at >= et.task_started_at
        AND (
            et.task_completed_at IS NULL
            OR qh.created_at < et.task_completed_at
        )
    WHERE et.task_started_at IS NOT NULL
    GROUP BY et.id
    HAVING COUNT(qh.id) > 0
)
UPDATE public.experiment_tasks et
SET
    chatbot_query_count = ptc.chatbot_count,
    queries_executed    = COALESCE(et.queries_executed, 0) + ptc.chatbot_count,
    total_interactions  = COALESCE(et.total_interactions, 0) + ptc.chatbot_count
FROM per_task_chatbot ptc
WHERE et.id = ptc.task_db_id
  AND et.chatbot_query_count = 0;

COMMIT;
