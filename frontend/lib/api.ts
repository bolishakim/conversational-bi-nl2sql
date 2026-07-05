import type { AuthResponse, LoginRequest, User } from "@/types/auth";
import type { HistoryResponse, QueryHistoryItem } from "@/types/history";
import type {
  ExperimentParticipant,
  ExperimentTask,
  ExperimentAccessCheck,
  RegisterParticipantRequest,
  RegisterParticipantResponse,
  LookupParticipantRequest,
  LookupParticipantResponse,
  OnboardingStatusResponse,
  ActiveExperimentResponse
} from "@/types/experiment";
import type {
  ParticipantSummary,
  ParticipantDetail,
  InteractionsResponse,
  TimelineEvent,
  ParticipantAnalytics,
  StudyOverview,
  TaskComparisonData,
  SurveyAnalytics,
  ChatbotAnalytics,
  ExportData,
} from "@/types/admin";
import { auth } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private baseURL: string;
  private refreshing: Promise<void> | null = null;
  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.startRefreshTimer();
  }

  // Start a background timer that checks token expiry every 60 seconds
  private startRefreshTimer() {
    if (typeof window === "undefined") return;
    if (this.refreshTimer) return;

    this.refreshTimer = setInterval(() => {
      if (auth.needsRefresh()) {
        this.refreshToken().catch(() => {});
      }
    }, 60000); // check every 60 seconds
  }

  // Refresh the token silently
  private async refreshToken(): Promise<void> {
    // Prevent multiple simultaneous refreshes
    if (this.refreshing) return this.refreshing;

    const token = auth.getToken();
    if (!token) return;

    this.refreshing = (async () => {
      try {
        const response = await fetch(`${this.baseURL}/api/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          auth.setToken(data.access_token);
        }
      } catch {
        // Silent failure — will retry on next interval
      } finally {
        this.refreshing = null;
      }
    })();

    return this.refreshing;
  }

  // Generic fetch wrapper
  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Auto-refresh if token is about to expire
    if (auth.needsRefresh()) {
      await this.refreshToken();
    }

    const token = auth.getToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    // Add auth header if token exists
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle non-200 responses
    if (!response.ok) {
      // Handle 401 Unauthorized - try refresh once before giving up
      if (response.status === 401) {
        // Attempt token refresh
        await this.refreshToken();
        const newToken = auth.getToken();

        if (newToken && newToken !== token) {
          // Retry the request with new token
          headers["Authorization"] = `Bearer ${newToken}`;
          const retryResponse = await fetch(`${this.baseURL}${endpoint}`, {
            ...options,
            headers,
          });

          if (retryResponse.ok) {
            return retryResponse.json();
          }
        }

        // Refresh failed — redirect to login
        auth.removeToken();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        throw new Error("Authentication expired. Please login again.");
      }

      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : "An error occurred"
      );
    }

    return response.json();
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    return this.fetch<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  }

  async me(): Promise<User> {
    return this.fetch<User>("/api/auth/me");
  }

  async logout(): Promise<void> {
    return this.fetch<void>("/api/auth/logout", {
      method: "POST",
    });
  }

  // Query endpoints
  async query(text: string): Promise<any> {
    return this.fetch("/api/v1/query", {
      method: "POST",
      body: JSON.stringify({ query: text }),
    });
  }

  // History endpoints
  async getHistory(limit: number = 50, offset: number = 0): Promise<HistoryResponse> {
    return this.fetch<HistoryResponse>(`/api/v1/history?limit=${limit}&offset=${offset}`);
  }

  async getHistoryItem(queryId: string): Promise<QueryHistoryItem> {
    return this.fetch<QueryHistoryItem>(`/api/v1/history/${queryId}`);
  }

  async deleteHistoryItem(queryId: string): Promise<void> {
    return this.fetch<void>(`/api/v1/history/${queryId}`, {
      method: "DELETE",
    });
  }

  // Experiment endpoints
  async checkExperimentAccess(): Promise<ExperimentAccessCheck> {
    return this.fetch<ExperimentAccessCheck>("/api/v1/experiment/access-check");
  }

  // Append ?participant_id=<sessionStorage> to a path so the backend resolves
  // the correct row under the shared-account model. Returns the path unchanged
  // when there is no PARTICIPANT_ID yet (e.g. fresh tab before registration).
  private withParticipantId(path: string): string {
    if (typeof window === "undefined") return path;
    const pid = sessionStorage.getItem("PARTICIPANT_ID");
    if (!pid) return path;
    const sep = path.includes("?") ? "&" : "?";
    return `${path}${sep}participant_id=${encodeURIComponent(pid)}`;
  }

  async getMyParticipantInfo(): Promise<ExperimentParticipant & { enrolled: boolean }> {
    return this.fetch<ExperimentParticipant & { enrolled: boolean }>(
      this.withParticipantId("/api/v1/experiment/participants/me")
    );
  }

  async getMyTasks(): Promise<ExperimentTask[]> {
    return this.fetch<ExperimentTask[]>(
      this.withParticipantId("/api/v1/experiment/tasks")
    );
  }

  async startTask(taskDbId: string): Promise<{ message: string; task_started_at: string }> {
    return this.fetch<{ message: string; task_started_at: string }>("/api/v1/experiment/tasks/start", {
      method: "POST",
      body: JSON.stringify({ task_db_id: taskDbId }),
    });
  }

  async completeTask(
    taskDbId: string,
    submittedAnswer: string,
    taskDifficultyRating?: number,
    confidenceInAnswer?: number
  ): Promise<{ message: string; task_duration_seconds: number }> {
    return this.fetch<{ message: string; task_duration_seconds: number }>("/api/v1/experiment/tasks/complete", {
      method: "POST",
      body: JSON.stringify({
        task_db_id: taskDbId,
        submitted_answer: submittedAnswer,
        task_difficulty_rating: taskDifficultyRating,
        confidence_in_answer: confidenceInAnswer,
      }),
    });
  }

  async logInteraction(
    taskDbId: string,
    interactionType: string,
    data: Record<string, unknown> = {}
  ): Promise<{ interaction_id: string; interaction_sequence: number }> {
    return this.fetch<{ interaction_id: string; interaction_sequence: number }>("/api/v1/experiment/interactions/log", {
      method: "POST",
      body: JSON.stringify({
        task_db_id: taskDbId,
        interaction_type: interactionType,
        ...data,
      }),
    });
  }

  // Onboarding endpoints
  async getOnboardingStatus(): Promise<OnboardingStatusResponse> {
    return this.fetch<OnboardingStatusResponse>(
      this.withParticipantId("/api/v1/experiment/onboarding/status")
    );
  }

  async getActiveExperiment(): Promise<ActiveExperimentResponse> {
    return this.fetch<ActiveExperimentResponse>("/api/v1/experiment/onboarding/active-experiment");
  }

  async registerParticipant(data: RegisterParticipantRequest): Promise<RegisterParticipantResponse> {
    return this.fetch<RegisterParticipantResponse>("/api/v1/experiment/onboarding/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async submitPostStudySurvey(participantId: string, surveyResponses: Record<string, any>): Promise<{ message: string }> {
    return this.fetch<{ message: string }>("/api/v1/experiment/participants/survey", {
      method: "POST",
      body: JSON.stringify({
        participant_id: participantId,
        survey_responses: surveyResponses,
      }),
    });
  }

  async lookupParticipant(data: LookupParticipantRequest): Promise<LookupParticipantResponse> {
    return this.fetch<LookupParticipantResponse>("/api/v1/experiment/onboarding/lookup", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Dashboard endpoints
  async getDashboardKPIs(dashboard: string, params: Record<string, string>): Promise<any> {
    const queryString = new URLSearchParams(params).toString();
    return this.fetch(`/api/v1/dashboards/${dashboard}/kpis?${queryString}`);
  }

  async getDashboardChart(dashboard: string, chart: string, params: Record<string, string>): Promise<any> {
    const queryString = new URLSearchParams(params).toString();
    return this.fetch(`/api/v1/dashboards/${dashboard}/${chart}?${queryString}`);
  }

  // Streaming query endpoint
  async queryStream(
    text: string,
    onEvent: (event: StreamEvent) => void,
    signal?: AbortSignal
  ): Promise<any> {
    // Auto-refresh if token is about to expire
    if (auth.needsRefresh()) {
      await this.refreshToken();
    }

    let token = auth.getToken();

    let response = await fetch(`${this.baseURL}/api/v1/query/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query: text }),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Try refresh once
        await this.refreshToken();
        token = auth.getToken();
        if (token) {
          response = await fetch(`${this.baseURL}/api/v1/query/stream`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ query: text }),
            signal,
          });
        }

        if (!response.ok) {
          auth.removeToken();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          throw new Error("Authentication expired. Please login again.");
        }
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult: any = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);

            // Store final result
            if (data.type === "result") {
              finalResult = data.data;
            }
          } catch {
            // Ignore JSON parse errors
          }
        }
      }
    }

    return finalResult;
  }

  // Admin endpoints (admin-only access)
  async getAdminParticipants(): Promise<ParticipantSummary[]> {
    return this.fetch<ParticipantSummary[]>("/api/v1/admin/participants");
  }

  async getAdminParticipantDetail(participantId: string): Promise<ParticipantDetail> {
    return this.fetch<ParticipantDetail>(`/api/v1/admin/participants/${participantId}/summary`);
  }

  async getAdminParticipantInteractions(
    participantId: string,
    taskId?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<InteractionsResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
      ...(taskId && { task_id: taskId }),
    });
    return this.fetch<InteractionsResponse>(`/api/v1/admin/participants/${participantId}/interactions?${params}`);
  }

  async getAdminParticipantTimeline(participantId: string): Promise<TimelineEvent[]> {
    return this.fetch<TimelineEvent[]>(`/api/v1/admin/participants/${participantId}/timeline`);
  }

  async getAdminParticipantAnalytics(participantId: string): Promise<ParticipantAnalytics> {
    return this.fetch<ParticipantAnalytics>(`/api/v1/admin/participants/${participantId}/analytics`);
  }

  // Admin actions on a participant (exclude / withdraw / reassign / reinstate)
  async adminExcludeParticipant(participantId: string, reason: string) {
    return this.fetch<{ id: string; status: string; exclusion_reason: string }>(
      `/api/v1/admin/participants/${participantId}/actions/exclude`,
      { method: "POST", body: JSON.stringify({ reason }) }
    );
  }

  async adminWithdrawParticipant(participantId: string, reason?: string) {
    return this.fetch<{ id: string; status: string }>(
      `/api/v1/admin/participants/${participantId}/actions/withdraw`,
      { method: "POST", body: JSON.stringify({ reason: reason || null }) }
    );
  }

  async adminReassignCondition(
    participantId: string,
    newCondition: "control" | "experimental",
    reason: string
  ) {
    return this.fetch<{ id: string; condition_assigned: string }>(
      `/api/v1/admin/participants/${participantId}/actions/reassign`,
      {
        method: "POST",
        body: JSON.stringify({ new_condition: newCondition, reason }),
      }
    );
  }

  async adminReinstateParticipant(participantId: string) {
    return this.fetch<{ id: string; status: string }>(
      `/api/v1/admin/participants/${participantId}/actions/reinstate`,
      { method: "POST" }
    );
  }

  // Study-wide analytics endpoints (admin only)
  async getStudyOverview(): Promise<StudyOverview> {
    return this.fetch<StudyOverview>("/api/v1/admin/analytics/overview");
  }

  async getTaskComparison(): Promise<TaskComparisonData> {
    return this.fetch<TaskComparisonData>("/api/v1/admin/analytics/tasks");
  }

  async getSurveyAnalytics(): Promise<SurveyAnalytics> {
    return this.fetch<SurveyAnalytics>("/api/v1/admin/analytics/surveys");
  }

  async getChatbotAnalytics(): Promise<ChatbotAnalytics> {
    return this.fetch<ChatbotAnalytics>("/api/v1/admin/analytics/chatbot");
  }

  async getExportData(tables?: string): Promise<ExportData> {
    const params = tables ? `?tables=${tables}` : "";
    return this.fetch<ExportData>(`/api/v1/admin/analytics/export${params}`);
  }
}

// Stream event interface
export interface StreamEvent {
  type: "start" | "progress" | "result" | "error";
  stage?: string;
  status?: string;
  message?: string;
  query?: string;
  details?: Record<string, unknown>;
  data?: unknown;
}

export const api = new APIClient(API_BASE_URL);
