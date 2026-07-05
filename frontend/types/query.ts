import type { QueryResults, ChartData, Analysis } from "./message";

// Query Request/Response types
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
