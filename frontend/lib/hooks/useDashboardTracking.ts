import { useCallback, useEffect, useRef } from "react";
import { useTaskSession } from "@/contexts/TaskSessionContext";
import { api } from "@/lib/api";

interface DashboardInteraction {
  action: string;
  element: string;
  metadata?: Record<string, any>;
}

/**
 * Hook to track dashboard interactions for experiment data collection
 * Automatically logs clicks, filter changes, and other dashboard events
 */
export function useDashboardTracking(dashboardName: string) {
  const { currentTask, isCurrentTaskStarted } = useTaskSession();
  const interactionCountRef = useRef(0);
  const lastLogTimeRef = useRef<number>(0);

  // Track individual interaction
  const logInteraction = useCallback(
    async (interaction: DashboardInteraction) => {
      // Only log if task is active
      if (!currentTask || !isCurrentTaskStarted) {
        return;
      }

      try {
        // Increment interaction count
        interactionCountRef.current += 1;

        // Log to backend
        await api.logInteraction(
          currentTask.id,
          "dashboard_interaction",
          {
            dashboard_action: interaction.action,
            dashboard_element: `${dashboardName}:${interaction.element}`,
          }
        );

        console.log(`[Dashboard Tracking] ${dashboardName} - ${interaction.action} on ${interaction.element}`);
      } catch (error) {
        console.error("Failed to log dashboard interaction:", error);
      }
    },
    [currentTask, isCurrentTaskStarted, dashboardName]
  );

  // Track clicks on dashboard elements
  const trackClick = useCallback(
    (elementName: string, metadata?: Record<string, any>) => {
      logInteraction({
        action: "click",
        element: elementName,
        metadata,
      });
    },
    [logInteraction]
  );

  // Track filter changes
  const trackFilterChange = useCallback(
    (filterName: string, filterValue: any) => {
      logInteraction({
        action: "filter_change",
        element: filterName,
        metadata: { value: filterValue },
      });
    },
    [logInteraction]
  );

  // Track chart interactions (hover, zoom, etc.)
  const trackChartInteraction = useCallback(
    (chartName: string, interactionType: string) => {
      logInteraction({
        action: `chart_${interactionType}`,
        element: chartName,
      });
    },
    [logInteraction]
  );

  // Track page view (when dashboard is loaded)
  useEffect(() => {
    if (currentTask && isCurrentTaskStarted) {
      logInteraction({
        action: "page_view",
        element: "dashboard",
      });
    }
  }, [currentTask?.id, isCurrentTaskStarted, logInteraction]);

  // Return tracking functions and stats
  return {
    trackClick,
    trackFilterChange,
    trackChartInteraction,
    interactionCount: interactionCountRef.current,
  };
}
