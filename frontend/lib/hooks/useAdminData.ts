import useSWR from 'swr';
import { api } from '@/lib/api';
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
} from '@/types/admin';

/**
 * Hook to fetch all participants with summary stats
 * Polls every 30 seconds for near-real-time updates
 */
export function useAdminParticipants() {
  const { data, error, isLoading, mutate } = useSWR<ParticipantSummary[]>(
    'admin-participants',
    () => api.getAdminParticipants(),
    {
      refreshInterval: 30000, // Poll every 30 seconds
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  return {
    participants: data || [],
    loading: isLoading,
    error: error?.message || null,
    refresh: mutate,
  };
}

/**
 * Hook to fetch detailed participant information
 * Polls every 60 seconds (slower refresh for detail view)
 */
export function useAdminParticipantDetail(participantId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ParticipantDetail>(
    participantId ? `admin-participant-${participantId}` : null,
    participantId ? () => api.getAdminParticipantDetail(participantId) : null,
    {
      refreshInterval: 60000, // Poll every 60 seconds
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  return {
    participant: data || null,
    loading: isLoading,
    error: error?.message || null,
    refresh: mutate,
  };
}

/**
 * Hook to fetch participant interactions (paginated)
 * No auto-refresh - large dataset, manual refresh only
 */
export function useAdminParticipantInteractions(
  participantId: string | null,
  taskId?: string,
  limit: number = 100,
  offset: number = 0
) {
  const key = participantId
    ? `admin-interactions-${participantId}-${taskId || 'all'}-${limit}-${offset}`
    : null;

  const { data, error, isLoading, mutate } = useSWR<InteractionsResponse>(
    key,
    participantId ? () => api.getAdminParticipantInteractions(participantId, taskId, limit, offset) : null,
    {
      refreshInterval: 0, // No auto-refresh (too much data)
      revalidateOnFocus: false,
    }
  );

  return {
    interactions: data?.interactions || [],
    total: data?.total || 0,
    loading: isLoading,
    error: error?.message || null,
    refresh: mutate,
  };
}

/**
 * Hook to fetch participant activity timeline
 * No auto-refresh - chronological data doesn't change often
 */
export function useAdminParticipantTimeline(participantId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TimelineEvent[]>(
    participantId ? `admin-timeline-${participantId}` : null,
    participantId ? () => api.getAdminParticipantTimeline(participantId) : null,
    {
      refreshInterval: 0, // No auto-refresh
      revalidateOnFocus: true,
    }
  );

  return {
    timeline: data || [],
    loading: isLoading,
    error: error?.message || null,
    refresh: mutate,
  };
}

/**
 * Hook to fetch participant analytics (for charts)
 * No auto-refresh - analytics are relatively static
 */
export function useAdminParticipantAnalytics(participantId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<ParticipantAnalytics>(
    participantId ? `admin-analytics-${participantId}` : null,
    participantId ? () => api.getAdminParticipantAnalytics(participantId) : null,
    {
      refreshInterval: 0, // No auto-refresh
      revalidateOnFocus: true,
    }
  );

  return {
    analytics: data || null,
    loading: isLoading,
    error: error?.message || null,
    refresh: mutate,
  };
}

/**
 * Hook to fetch study-wide overview analytics
 */
export function useStudyOverview() {
  const { data, error, isLoading, mutate } = useSWR<StudyOverview>(
    'admin-study-overview',
    () => api.getStudyOverview(),
    { refreshInterval: 60000, revalidateOnFocus: true }
  );
  return { data: data || null, loading: isLoading, error: error?.message || null, refresh: mutate };
}

/**
 * Hook to fetch task comparison analytics
 */
export function useTaskComparison() {
  const { data, error, isLoading, mutate } = useSWR<TaskComparisonData>(
    'admin-task-comparison',
    () => api.getTaskComparison(),
    { refreshInterval: 0, revalidateOnFocus: true }
  );
  return { data: data || null, loading: isLoading, error: error?.message || null, refresh: mutate };
}

/**
 * Hook to fetch survey analytics
 */
export function useSurveyAnalytics() {
  const { data, error, isLoading, mutate } = useSWR<SurveyAnalytics>(
    'admin-survey-analytics',
    () => api.getSurveyAnalytics(),
    { refreshInterval: 0, revalidateOnFocus: true }
  );
  return { data: data || null, loading: isLoading, error: error?.message || null, refresh: mutate };
}

/**
 * Hook to fetch chatbot analytics
 */
export function useChatbotAnalytics() {
  const { data, error, isLoading, mutate } = useSWR<ChatbotAnalytics>(
    'admin-chatbot-analytics',
    () => api.getChatbotAnalytics(),
    { refreshInterval: 0, revalidateOnFocus: true }
  );
  return { data: data || null, loading: isLoading, error: error?.message || null, refresh: mutate };
}
