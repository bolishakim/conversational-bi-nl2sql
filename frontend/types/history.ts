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
