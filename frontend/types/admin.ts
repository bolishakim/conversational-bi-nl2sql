// Admin-related TypeScript types

export interface ParticipantSummary {
  id: string;
  participant_code: string;
  condition_assigned: string;
  status: string;
  tasks_completed: number;
  tasks_total: number;
  session_duration_minutes: number | null;
  avg_task_duration_seconds: number | null;
  last_activity: string | null;
  recruitment_source?: 'university' | 'prolific' | null;
  prolific_pid?: string | null;
}

export interface ParticipantDetail extends ParticipantSummary {
  age: number | null;
  age_range: string | null;
  occupation_statuses: string | null;
  occupation_status: string | null;
  field_of_work: string | null;
  field_of_study: string | null;
  visual_analytics_frequency: string | null;
  business_background: string | null;
  llm_chatbot_experience: string | null;
  bi_tools_experience: string | null;
  registered_at: string | null;
  first_task_at: string | null;
  last_task_at: string | null;
  exclusion_reason?: string | null;
  admin_notes?: string | null;
  withdrawal_requested?: boolean | null;
  withdrawal_timestamp?: string | null;
}

export interface InteractionLog {
  id: string;
  interaction_sequence: number;
  interaction_timestamp: string;
  interaction_type: string;
  task_id: string;
  task_number: number | null;
  query_text: string | null;
  dashboard_action: string | null;
  dashboard_element: string | null;
  tokens_used: number | null;
  cost_usd: string | null;
}

export interface InteractionsResponse {
  interactions: InteractionLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: 'task_started' | 'interaction' | 'task_completed';
  task_number: number | null;
  details: Record<string, any>;
}

export interface ParticipantAnalytics {
  interactions_by_type: Array<{ type: string; count: number }>;
  interactions_over_time: Array<{ timestamp: string; count: number }>;
  dashboard_elements_clicked: Array<{ element: string; count: number }>;
  task_durations: Array<{ task_number: number; duration_seconds: number }>;
}

// Study-wide analytics types

export interface StudyOverview {
  total_participants: number;
  control_count: number;
  experimental_count: number;
  completed_count: number;
  survey_completed_count: number;
  avg_session_duration_minutes: number | null;
  completion_rate_percent: number;
  enrollment_over_time: Array<{ date: string; control: number; experimental: number; cumulative: number }>;
  completion_funnel: Array<{ stage: string; count: number }>;
}

export interface TaskConditionStats {
  avg_duration: number | null;
  avg_difficulty: number | null;
  avg_confidence: number | null;
  avg_interactions: number | null;
  avg_quality: number | null;
  completion_count: number;
  avg_chatbot_queries?: number | null;
}

export interface TaskComparisonData {
  tasks: Array<{
    task_number: number;
    domain: string | null;
    complexity_level: string | null;
    control: TaskConditionStats;
    experimental: TaskConditionStats;
  }>;
  overall: {
    control_avg_duration: number | null;
    experimental_avg_duration: number | null;
    control_avg_quality: number | null;
    experimental_avg_quality: number | null;
  };
}

export interface LikertComparison {
  control_avg: number | null;
  experimental_avg: number | null;
  control_dist: number[];
  experimental_dist: number[];
}

export interface LikertStats {
  avg: number | null;
  distribution: number[];
}

export interface SurveyAnalytics {
  pre_survey: Record<string, Array<{ value: string; control: number; experimental: number }>>;
  post_survey: {
    common: Record<string, LikertComparison>;
    experimental_only: Record<string, LikertStats>;
    open_feedback: Array<{ participant_code: string; condition: string; type?: string; feedback: string }>;
  };
}

export interface ChatbotAnalytics {
  total_queries: number;
  success_rate_percent: number;
  avg_execution_time_ms: number | null;
  total_tokens: number;
  total_cost_usd: number;
  avg_queries_per_participant: number;
  domain_breakdown: Array<{ domain: string; count: number }>;
  queries_over_time: Array<{ date: string; count: number }>;
  token_usage_by_participant: Array<{ participant_code: string; total_tokens: number; total_cost: number; query_count: number }>;
  error_stages: Array<{ stage: string; count: number }>;
}

export interface ExportData {
  exported_at: string;
  participants?: any[];
  tasks?: any[];
  interactions?: any[];
  query_history?: any[];
}
