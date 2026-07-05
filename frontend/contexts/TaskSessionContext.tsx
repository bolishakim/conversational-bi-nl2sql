"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { ExperimentTask } from "@/types/experiment";

interface TaskSessionState {
  // User tracking
  userId: string | null;

  // Session state
  sessionStarted: boolean;
  currentTaskIndex: number;
  tasks: ExperimentTask[];

  // Current task state
  currentTask: ExperimentTask | null;
  elapsedSeconds: number;

  // Loading states
  loading: boolean;
  error: string | null;
  initialized: boolean;
}

interface TaskSessionContextType extends TaskSessionState {
  // Actions
  initializeForUser: (userId: string) => Promise<void>;
  resetSession: () => void;
  startSession: () => Promise<void>;
  startCurrentTask: () => Promise<void>;
  submitAnswer: (answer: string, difficulty: number, confidence: number) => Promise<void>;
  goToNextTask: () => void;
  refreshTasks: () => Promise<void>;

  // Computed
  completedCount: number;
  totalCount: number;
  allTasksCompleted: boolean;
  isCurrentTaskStarted: boolean;
  isCurrentTaskCompleted: boolean;
}

const initialState: TaskSessionState = {
  userId: null,
  sessionStarted: false,
  currentTaskIndex: 0,
  tasks: [],
  currentTask: null,
  elapsedSeconds: 0,
  loading: false,
  error: null,
  initialized: false,
};

const TaskSessionContext = createContext<TaskSessionContextType | undefined>(undefined);

export function TaskSessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<TaskSessionState>(initialState);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const currentUserIdRef = useRef<string | null>(null);

  // Clear timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // Timer effect - runs for the current task based on task_started_at from database
  useEffect(() => {
    // Clear existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Only run timer if task is started but not completed
    if (state.currentTask?.task_started_at && !state.currentTask?.task_completed_at) {
      const startTime = new Date(state.currentTask.task_started_at).getTime();

      // Update immediately
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setState(prev => ({ ...prev, elapsedSeconds: elapsed }));

      // Then update every second
      timerRef.current = setInterval(() => {
        const newElapsed = Math.floor((Date.now() - startTime) / 1000);
        setState(prev => ({ ...prev, elapsedSeconds: newElapsed }));
      }, 1000);
    } else {
      setState(prev => ({ ...prev, elapsedSeconds: 0 }));
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [state.currentTask?.id, state.currentTask?.task_started_at, state.currentTask?.task_completed_at]);

  const loadTasksForUser = async (userId: string) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      const tasksData = await api.getMyTasks();

      // Sort by task number
      const sortedTasks = tasksData.sort((a: ExperimentTask, b: ExperimentTask) =>
        a.task_number - b.task_number
      );

      // Find the first incomplete task
      let currentIndex = sortedTasks.findIndex((t: ExperimentTask) => !t.task_completed_at);
      if (currentIndex === -1) {
        currentIndex = sortedTasks.length; // All completed
      }

      // Determine if session was already started (any task has been started)
      const sessionStarted = sortedTasks.some((t: ExperimentTask) => t.task_started_at);

      const currentTask = sortedTasks[currentIndex] || null;

      setState(prev => ({
        ...prev,
        userId,
        tasks: sortedTasks,
        currentTaskIndex: currentIndex,
        currentTask,
        sessionStarted,
        loading: false,
        initialized: true,
      }));
    } catch (err: any) {
      console.error("Error loading tasks:", err);
      setState(prev => ({
        ...prev,
        loading: false,
        error: err.message || "Failed to load tasks",
        initialized: true,
      }));
    }
  };

  const initializeForUser = useCallback(async (userId: string) => {
    // If same user, just refresh
    if (currentUserIdRef.current === userId && state.initialized) {
      await loadTasksForUser(userId);
      return;
    }

    // Different user - reset everything and load fresh
    currentUserIdRef.current = userId;

    // Clear timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Reset state completely
    setState({
      ...initialState,
      loading: true,
    });

    // Load tasks for new user
    await loadTasksForUser(userId);
  }, [state.initialized]);

  const resetSession = useCallback(() => {
    // Clear timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    currentUserIdRef.current = null;
    setState(initialState);
  }, []);

  const startSession = useCallback(async () => {
    setState(prev => ({ ...prev, sessionStarted: true }));
  }, []);

  const startCurrentTask = useCallback(async () => {
    if (!state.currentTask) return;

    try {
      setState(prev => ({ ...prev, loading: true }));
      await api.startTask(state.currentTask!.id);

      // Refresh to get updated task data with task_started_at
      if (state.userId) {
        await loadTasksForUser(state.userId);
      }
    } catch (err: any) {
      console.error("Error starting task:", err);
      setState(prev => ({
        ...prev,
        loading: false,
        error: err.message || "Failed to start task",
      }));
    }
  }, [state.currentTask, state.userId]);

  const submitAnswer = useCallback(async (
    answer: string,
    difficulty: number,
    confidence: number
  ) => {
    if (!state.currentTask) return;

    try {
      setState(prev => ({ ...prev, loading: true }));
      await api.completeTask(state.currentTask!.id, answer, difficulty, confidence);

      // Stop timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      // Refresh tasks to get updated data
      if (state.userId) {
        await loadTasksForUser(state.userId);
      }
    } catch (err: any) {
      console.error("Error submitting answer:", err);
      setState(prev => ({
        ...prev,
        loading: false,
        error: err.message || "Failed to submit answer",
      }));
      throw err;
    }
  }, [state.currentTask, state.userId]);

  const goToNextTask = useCallback(() => {
    const nextIndex = state.currentTaskIndex + 1;
    if (nextIndex < state.tasks.length) {
      setState(prev => ({
        ...prev,
        currentTaskIndex: nextIndex,
        currentTask: prev.tasks[nextIndex],
        elapsedSeconds: 0,
      }));
    }
  }, [state.currentTaskIndex, state.tasks.length]);

  const refreshTasks = useCallback(async () => {
    if (state.userId) {
      await loadTasksForUser(state.userId);
    }
  }, [state.userId]);

  // Computed values
  // Exclude tutorial tasks from progress calculations
  const realTasks = state.tasks.filter(t => !t.is_tutorial);
  const completedCount = realTasks.filter(t => t.task_completed_at).length;
  const totalCount = realTasks.length;
  const allTasksCompleted = totalCount > 0 && completedCount === totalCount;
  const isCurrentTaskStarted = !!state.currentTask?.task_started_at;
  const isCurrentTaskCompleted = !!state.currentTask?.task_completed_at;

  const value: TaskSessionContextType = {
    ...state,
    initializeForUser,
    resetSession,
    startSession,
    startCurrentTask,
    submitAnswer,
    goToNextTask,
    refreshTasks,
    completedCount,
    totalCount,
    allTasksCompleted,
    isCurrentTaskStarted,
    isCurrentTaskCompleted,
  };

  return (
    <TaskSessionContext.Provider value={value}>
      {children}
    </TaskSessionContext.Provider>
  );
}

export function useTaskSession() {
  const context = useContext(TaskSessionContext);
  if (context === undefined) {
    throw new Error("useTaskSession must be used within a TaskSessionProvider");
  }
  return context;
}
