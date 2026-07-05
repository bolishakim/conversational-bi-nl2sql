// Chat Message types
export interface Analysis {
  summary: string;
  key_insights: string[];
  data_quality_notes: string[];
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
