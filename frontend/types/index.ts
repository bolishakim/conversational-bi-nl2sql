// User types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin?: boolean;
  role: 'admin' | 'participant_control' | 'participant_experimental';
  can_access_chatbot: boolean;
  can_access_dashboards: boolean;
  can_access_admin: boolean;
  created_at: string;
}

// Experiment types
export interface ExperimentParticipant {
  id: string;
  participant_code: string;
  condition_assigned: 'control' | 'experimental';
  status: string;
  consent_given: boolean;
  tasks_completed: number;
  tasks_attempted: number;
  experiment_id?: string;
  // Pre-survey responses (anonymous - no PII)
  age?: number;
  age_range?: string; // legacy
  occupation_statuses?: string; // comma-separated
  occupation_status?: string; // legacy
  field_of_work?: string;
  field_of_study?: string;
  visual_analytics_frequency?: string;
  business_background?: string;
  llm_chatbot_experience?: string;
  bi_tools_experience?: string;
  // Post-study survey
  post_study_survey_responses?: Record<string, any> | null;
  // Registration tracking
  registered_at?: string;
  onboarding_completed?: boolean;
}

// Pre-survey option types
export type OccupationOption = 'student' | 'employee' | 'self_employed' | 'other';
export type FieldOfWork = 'business' | 'computer_science' | 'engineering' | 'natural_sciences' | 'social_sciences' | 'other';
export type VisualAnalyticsFrequency = 'never' | 'rarely' | 'occasionally' | 'regularly' | 'daily';
export type BusinessBackground = 'education' | 'experience' | 'both' | 'none';
export type LLMChatbotExperience = 'never' | 'once_twice' | 'occasionally' | 'regularly';
export type BIToolsExperience = 'none' | 'minimal' | 'basic' | 'intermediate' | 'advanced';

// Onboarding types
export interface RegisterParticipantRequest {
  experiment_id: string;
  // Pre-survey questions
  age: number;
  occupation_statuses: string[];
  field_of_work?: string;
  field_of_study?: string;
  visual_analytics_frequency: VisualAnalyticsFrequency;
  business_background: BusinessBackground;
  llm_chatbot_experience: LLMChatbotExperience;
  bi_tools_experience: BIToolsExperience;
  // Consent
  consent_given: boolean;
  // Prolific identifiers (optional; populated when arriving via Prolific URL)
  prolific_pid?: string;
  prolific_study_id?: string;
  prolific_session_id?: string;
  // Condition forced by Prolific study URL (?condition=control|experimental).
  // Honored only when prolific_pid is also present.
  prolific_condition?: 'control' | 'experimental';
}

export interface RegisterParticipantResponse {
  success: boolean;
  message: string;
  participant_code: string;
  condition_assigned: 'control' | 'experimental';
  participant_id: string;
}

// Simplified lookup - only needs participant code now (no DOB since we don't collect it)
export interface LookupParticipantRequest {
  participant_code: string;
}

export interface LookupParticipantResponse {
  found: boolean;
  participant?: ExperimentParticipant;
  message: string;
}

export interface OnboardingStatusResponse {
  needs_onboarding: boolean;
  participant?: ExperimentParticipant;
  message: string;
}

export interface ActiveExperimentResponse {
  has_active_experiment: boolean;
  experiment_id?: string;
  experiment_name?: string;
  message: string;
}

export interface ExperimentTask {
  id: string;
  task_id: string;
  task_number: number;
  task_description: string;
  task_type?: string;
  domain?: string;
  complexity_level?: string;
  task_started_at?: string;
  task_completed_at?: string;
  task_duration_seconds?: number;
  submitted_answer?: string;
}

export interface ExperimentAccessCheck {
  user_id: string;
  role: string;
  can_access_chatbot: boolean;
  can_access_dashboards: boolean;
  can_access_admin: boolean;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// API Error
export interface APIError {
  detail: string | { msg: string }[];
}

// Analysis structure from backend
export interface Analysis {
  summary: string;
  key_insights: string[];
  recommendations: string[];
  data_quality_notes: string[];
}

// Chat Message types
export interface Message {
  id: string;
  role: "user" | "system";
  content: string;
  timestamp: Date;
  sqlQuery?: string;
  results?: QueryResults;
  chart?: ChartData;
  analysis?: Analysis;
  error?: string;
}

export interface QueryResults {
  columns: string[];
  data: any[][];
  row_count: number;
}

export interface ChartData {
  data: any[];
  layout: any;
  config?: any;
}

// Query Request/Response
export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  query_id: string;
  user_query: string;
  sql_query: string;
  results: QueryResults;
  chart?: ChartData;
  analysis: Analysis;
  execution_time_ms: number;
}

// History types
export interface QueryHistoryItem {
  id: string;
  user_query: string;
  domain?: string;
  orchestrator_action?: string;
  generated_sql?: string;
  sql_explanation?: string;
  execution_status?: string;
  execution_error?: string;
  result_data?: any;
  row_count?: number;
  execution_time_ms?: number;
  analysis?: {
    summary?: string;
    key_insights?: string[];
    recommendations?: string[];
    data_quality_notes?: string[];
  };
  chart_type?: string;
  chart_config?: any;
  total_duration_ms?: number;
  created_at: string;
  error_occurred?: boolean;
  error_details?: string;
}

export interface HistoryResponse {
  queries: QueryHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}
