"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import { useTaskSession } from "@/contexts/TaskSessionContext";
import type { ExperimentParticipant } from "@/types/experiment";
import { api } from "@/lib/api";
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  PlayCircle,
  AlertCircle,
  Rocket,
  BarChart3,
  MessageSquare
} from "lucide-react";

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function TasksPage() {
  const router = useRouter();
  const {
    sessionStarted,
    tasks,
    currentTask,
    elapsedSeconds,
    loading,
    error,
    completedCount,
    totalCount,
    allTasksCompleted,
    isCurrentTaskStarted,
    isCurrentTaskCompleted,
    startSession,
    initializeForUser,
  } = useTaskSession();

  const [participant, setParticipant] = useState<ExperimentParticipant | null>(null);
  const [starting, setStarting] = useState(false);
  const [initializing, setInitializing] = useState(true);

  // Initialize task session for current user
  useEffect(() => {
    initializeUserSession();
  }, []);

  const initializeUserSession = async () => {
    try {
      setInitializing(true);
      const status = await api.getOnboardingStatus();

      if (status.participant) {
        setParticipant(status.participant as ExperimentParticipant);
        // Initialize task session for this specific user
        await initializeForUser(status.participant.id);
      }
    } catch (err) {
      console.error("Error initializing session:", err);
    } finally {
      setInitializing(false);
    }
  };

  const handleStartSession = async () => {
    setStarting(true);
    try {
      await startSession();
      // Navigate to current task - user will see "Ready to Start Task?" confirmation
      if (currentTask) {
        router.push(`/tasks/${currentTask.id}`);
      }
    } finally {
      setStarting(false);
    }
  };

  const handleContinueTask = () => {
    // Don't navigate if all tasks are completed
    if (currentTask && !allTasksCompleted) {
      router.push(`/tasks/${currentTask.id}`);
    }
  };

  // Calculate real task counts (exclude tutorial)
  const realTasks = tasks.filter(t => !t.is_tutorial);
  const realCompletedCount = realTasks.filter(t => t.task_completed_at).length;
  const realTotalCount = realTasks.length;
  const progressPercent = realTotalCount > 0 ? Math.round((realCompletedCount / realTotalCount) * 100) : 0;
  const isLoading = initializing || loading;

  return (
    <AuthenticatedLayout
      title="Study Tasks"
      subtitle="Complete the tasks below as part of the research study"
    >
      <div className="p-6 space-y-6 max-w-4xl mx-auto">
        {/* Progress Overview */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Your Progress</h2>
              <p className="text-sm text-gray-500 mt-1">
                {realCompletedCount} of {realTotalCount} tasks completed
              </p>
            </div>
            <div className="text-right">
              <span className="text-3xl font-bold text-blue-600">{progressPercent}%</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Status Messages */}
          {allTasksCompleted && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  All tasks completed! Thank you for participating.
                </span>
              </div>
            </div>
          )}

          {/* Show timer if task is in progress */}
          {isCurrentTaskStarted && !isCurrentTaskCompleted && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <PlayCircle className="w-5 h-5 text-yellow-600" />
                  <span className="text-sm font-medium text-yellow-800">
                    {currentTask?.is_tutorial ? 'Tutorial' : `Task ${currentTask?.task_number}`} in progress
                  </span>
                </div>
                <div className="flex items-center gap-2 text-yellow-700">
                  <Clock className="w-4 h-4" />
                  <span className="font-mono">{formatDuration(elapsedSeconds)}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Loading tasks...</p>
          </div>
        )}

        {/* No Tasks State */}
        {!isLoading && tasks.length === 0 && !error && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <ClipboardList className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Tasks Available</h3>
            <p className="text-gray-500">
              Tasks for this study have not been assigned yet.
              Please check back later or contact the researcher.
            </p>
          </div>
        )}

        {/* Main Content - Session Not Started Yet */}
        {!isLoading && tasks.length > 0 && !sessionStarted && !allTasksCompleted && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 shadow-sm text-center">
            <Rocket className="w-20 h-20 text-blue-500 mx-auto mb-6" />
            <h3 className="text-2xl font-semibold text-gray-900 mb-3">Ready to Begin?</h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              You have <span className="font-semibold text-blue-600">1 tutorial + {realTotalCount} tasks</span> to complete.
              The tutorial will help you familiarize yourself with the system. Tasks will be presented one at a time, and a timer will track your progress on each task.
            </p>

            {/* Available Tools Info */}
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-4 mb-6 text-left max-w-md mx-auto">
              <h4 className="font-medium text-blue-900 mb-2">Available Tools</h4>
              <div className="flex flex-wrap gap-3 mb-2">
                <a href="/dashboards/sales" className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-blue-200 hover:bg-blue-50 transition-colors">
                  <BarChart3 className="w-4 h-4 text-blue-600" />
                  <span className="text-sm text-blue-800">Dashboards</span>
                </a>
                {participant?.condition_assigned === "experimental" && (
                  <a href="/chat" className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-blue-200 hover:bg-blue-50 transition-colors">
                    <MessageSquare className="w-4 h-4 text-blue-600" />
                    <span className="text-sm text-blue-800">AI Chatbot</span>
                  </a>
                )}
              </div>
              <p className="text-sm text-blue-700">
                You can navigate to dashboards{participant?.condition_assigned === "experimental" ? " and the chatbot" : ""} while working on tasks. Your timer will continue running.
              </p>
            </div>

            <button
              onClick={handleStartSession}
              disabled={starting}
              className="px-8 py-4 bg-blue-600 text-white font-semibold text-lg rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
            >
              {starting ? "Starting..." : "Start Tasks"}
            </button>
          </div>
        )}

        {/* All Tasks Completed - Redirect to Post-Study Survey */}
        {!isLoading && tasks.length > 0 && allTasksCompleted && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 shadow-sm text-center">
            <CheckCircle2 className="w-20 h-20 text-green-500 mx-auto mb-6" />
            <h3 className="text-2xl font-semibold text-gray-900 mb-3">All Tasks Completed!</h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Thank you! All {realTotalCount} tasks have been completed successfully.
              Please complete a brief post-study survey to finish the experiment.
            </p>
            <button
              onClick={() => router.push("/survey")}
              className="px-8 py-4 bg-blue-600 text-white font-semibold text-lg rounded-xl hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
            >
              Go to Post-Study Survey
            </button>
          </div>
        )}

        {/* Session Started - Show Current Task Status */}
        {!isLoading && tasks.length > 0 && sessionStarted && !allTasksCompleted && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 shadow-sm text-center">
            {isCurrentTaskStarted && !isCurrentTaskCompleted ? (
              <>
                <PlayCircle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {currentTask?.is_tutorial ? 'Tutorial Task' : `Task ${currentTask?.task_number}`} In Progress
                </h3>
                <p className="text-gray-600 mb-2">
                  Your timer is running. Click below to continue working on this task.
                </p>
                <div className="flex items-center justify-center gap-2 text-2xl font-mono text-yellow-600 mb-6">
                  <Clock className="w-6 h-6" />
                  <span>{formatDuration(elapsedSeconds)}</span>
                </div>
                <button
                  onClick={handleContinueTask}
                  className="px-8 py-4 bg-yellow-500 text-white font-semibold text-lg rounded-xl hover:bg-yellow-600 transition-colors shadow-lg hover:shadow-xl"
                >
                  Continue Task
                </button>
              </>
            ) : (
              <>
                <ClipboardList className="w-16 h-16 text-blue-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {currentTask?.is_tutorial ? 'Tutorial Task' : `Task ${currentTask?.task_number} of ${realTotalCount}`}
                </h3>
                <p className="text-gray-600 mb-6">
                  Click below to start this task. The timer will begin when you start.
                </p>
                <button
                  onClick={handleContinueTask}
                  className="px-8 py-4 bg-blue-600 text-white font-semibold text-lg rounded-xl hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
                >
                  {currentTask?.is_tutorial ? 'Start Tutorial' : `Go to Task ${currentTask?.task_number}`}
                </button>
              </>
            )}
          </div>
        )}


        {/* Instructions Footer */}
        {!isLoading && tasks.length > 0 && !allTasksCompleted && (
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
            <h4 className="font-medium text-gray-900 mb-2">Instructions</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>Tasks are presented one at a time in sequence</li>
              <li>A timer tracks your time on each task separately</li>
              <li>You can navigate to dashboards{participant?.condition_assigned === "experimental" ? " and the chatbot" : ""} while working - your timer continues</li>
              <li>Take your time - accuracy is more important than speed</li>
            </ul>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
