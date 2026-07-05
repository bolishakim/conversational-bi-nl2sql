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
  // Tutorial fields
  is_tutorial?: boolean;
  tutorial_steps?: string;
  tutorial_tips?: string;
}

export interface ExperimentAccessCheck {
  user_id: string;
  role: string;
  can_access_chatbot: boolean;
  can_access_dashboards: boolean;
  can_access_admin: boolean;
}
