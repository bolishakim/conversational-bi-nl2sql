"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import { useTaskSession } from "@/contexts/TaskSessionContext";
import { api } from "@/lib/api";
import type { ExperimentParticipant } from "@/types/experiment";
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  Send,
  PlayCircle,
  FileText,
  BarChart3,
  MessageSquare,
  ArrowRight
} from "lucide-react";
import ReactMarkdown from "react-markdown";

const getDraftKey = (id: string) => `task_draft_${id}`;

interface TaskPageProps {
  params: Promise<{ taskId: string }>;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} seconds`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function TaskDetailPage({ params }: TaskPageProps) {
  const { taskId } = use(params);
  const router = useRouter();

  const {
    currentTask,
    elapsedSeconds,
    loading: contextLoading,
    isCurrentTaskStarted,
    isCurrentTaskCompleted,
    startCurrentTask,
    submitAnswer,
    totalCount,
    completedCount,
    allTasksCompleted,
    refreshTasks,
    initializeForUser,
    initialized,
  } = useTaskSession();

  const [participant, setParticipant] = useState<ExperimentParticipant | null>(null);
  const [initializing, setInitializing] = useState(true);

  // Form state — initialized from sessionStorage to survive page navigation
  const [answer, setAnswer] = useState(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem(getDraftKey(taskId)) || "";
    }
    return "";
  });
  const [difficultyRating, setDifficultyRating] = useState<number | null>(() => {
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem(`${getDraftKey(taskId)}_difficulty`);
      return saved ? Number(saved) : null;
    }
    return null;
  });
  const [confidenceRating, setConfidenceRating] = useState<number | null>(() => {
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem(`${getDraftKey(taskId)}_confidence`);
      return saved ? Number(saved) : null;
    }
    return null;
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [autoStarted, setAutoStarted] = useState(false);

  // Sync form state to sessionStorage
  useEffect(() => {
    if (answer) {
      sessionStorage.setItem(getDraftKey(taskId), answer);
    } else {
      sessionStorage.removeItem(getDraftKey(taskId));
    }
  }, [answer, taskId]);

  useEffect(() => {
    if (difficultyRating !== null) {
      sessionStorage.setItem(`${getDraftKey(taskId)}_difficulty`, String(difficultyRating));
    } else {
      sessionStorage.removeItem(`${getDraftKey(taskId)}_difficulty`);
    }
  }, [difficultyRating, taskId]);

  useEffect(() => {
    if (confidenceRating !== null) {
      sessionStorage.setItem(`${getDraftKey(taskId)}_confidence`, String(confidenceRating));
    } else {
      sessionStorage.removeItem(`${getDraftKey(taskId)}_confidence`);
    }
  }, [confidenceRating, taskId]);

  // Initialize session for current user
  useEffect(() => {
    const initializeUserSession = async () => {
      try {
        setInitializing(true);
        const status = await api.getOnboardingStatus();

        if (status.participant) {
          setParticipant(status.participant as ExperimentParticipant);
          await initializeForUser(status.participant.id);
        }
      } catch (err) {
        console.error("Error initializing session:", err);
      } finally {
        setInitializing(false);
      }
    };

    initializeUserSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Check if this is the correct task and redirect if not
  useEffect(() => {
    const currentTaskId = currentTask?.id;
    if (!initializing && !contextLoading && initialized && currentTaskId && currentTaskId !== taskId) {
      router.replace(`/tasks/${currentTaskId}`);
    }
  }, [initializing, contextLoading, initialized, currentTask?.id, taskId, router]);

  // Redirect to tasks page if all tasks are completed
  useEffect(() => {
    if (!initializing && !contextLoading && initialized && allTasksCompleted) {
      router.replace('/tasks');
    }
  }, [initializing, contextLoading, initialized, allTasksCompleted, router]);

  // Auto-start task once (state-based, not ref-based to avoid loop)
  useEffect(() => {
    if (!initializing && !contextLoading && currentTask && currentTask.id === taskId && !isCurrentTaskStarted && !isCurrentTaskCompleted && !autoStarted) {
      setAutoStarted(true);
      startCurrentTask().catch(err => {
        console.error("Auto-start error:", err);
        setAutoStarted(false); // Reset on error so user can try manually
      });
    }
  }, [initializing, contextLoading, currentTask?.id, taskId, isCurrentTaskStarted, isCurrentTaskCompleted, autoStarted, startCurrentTask]);

  const handleStartTask = async () => {
    try {
      setSubmitting(true);
      setSubmitError(null);
      await startCurrentTask();
    } catch (err: any) {
      console.error("Error starting task:", err);
      setSubmitError(err.message || "Failed to start task");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) {
      setSubmitError("Please enter your answer before submitting");
      return;
    }

    if (difficultyRating === null) {
      setSubmitError("Please rate the task difficulty");
      return;
    }

    if (confidenceRating === null) {
      setSubmitError("Please rate your confidence in the answer");
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);

      await submitAnswer(answer, difficultyRating, confidenceRating);
      sessionStorage.removeItem(getDraftKey(taskId));
      sessionStorage.removeItem(`${getDraftKey(taskId)}_difficulty`);
      sessionStorage.removeItem(`${getDraftKey(taskId)}_confidence`);
      setShowSuccess(true);
    } catch (err: any) {
      console.error("Error submitting task:", err);
      setSubmitError(err.message || "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextTask = async () => {
    try {
      // Refresh tasks first
      await refreshTasks();
    } catch (err) {
      console.error("Error refreshing tasks:", err);
    }

    // Force full page reload to /tasks
    window.location.href = "/tasks";
  };

  // Rating labels
  const difficultyLabels = ["Very Easy", "Easy", "Moderate", "Difficult", "Very Difficult"];
  const confidenceLabels = ["Not Confident", "Slightly", "Moderately", "Confident", "Very Confident"];

  const isLoading = initializing || contextLoading;

  // Show loading while initializing
  if (isLoading) {
    return (
      <AuthenticatedLayout title="Loading..." subtitle="">
        <div className="p-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Loading task...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  // Show loading state while initializing
  if (initializing || contextLoading || !currentTask) {
    return (
      <AuthenticatedLayout title="Loading..." subtitle="">
        <div className="p-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Loading task...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  // totalCount from context already excludes tutorial
  const realTotalCount = totalCount;

  return (
    <AuthenticatedLayout
      title={currentTask.is_tutorial ? 'Tutorial Task' : `Task ${currentTask.task_number} of ${realTotalCount}`}
      subtitle={currentTask.domain ? `Domain: ${currentTask.domain}` : ""}
    >
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Status & Timer Bar */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Status Badge */}
              {isCurrentTaskCompleted ? (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Completed</span>
                </div>
              ) : isCurrentTaskStarted ? (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-full text-sm font-medium">
                  <PlayCircle className="w-4 h-4" />
                  <span>In Progress</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
                  <Clock className="w-4 h-4" />
                  <span>Not Started</span>
                </div>
              )}

              {/* Progress indicator */}
              <span className="text-sm text-gray-500">
                {currentTask.is_tutorial ? 'Tutorial' : `Task ${currentTask.task_number} of ${realTotalCount}`}
              </span>
            </div>

            {/* Timer - shows elapsed time for this specific task (NOT for tutorial) */}
            {isCurrentTaskStarted && !currentTask.is_tutorial && (
              <div className="flex items-center gap-2 text-gray-600">
                <Clock className="w-4 h-4" />
                <span className="font-mono text-lg">
                  {isCurrentTaskCompleted && currentTask.task_duration_seconds
                    ? formatDuration(currentTask.task_duration_seconds)
                    : formatDuration(elapsedSeconds)
                  }
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Tutorial Badge - Only for tutorial tasks */}
        {currentTask.is_tutorial && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">🎓</span>
              <h2 className="text-2xl font-bold text-blue-900">TUTORIAL TASK</h2>
            </div>
            <p className="text-blue-800 text-base">
              This is a <strong>practice task</strong> to familiarize yourself with the system.
              Take your time to explore the interface and tools.{" "}
              <strong className="text-blue-900">
                Your performance on this task is NOT analyzed or scored.
              </strong>
            </p>
          </div>
        )}


        {/* Task Description - Only shown when task is started */}
        {isCurrentTaskStarted && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <div className="flex items-start gap-3 mb-4">
              <FileText className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Task Description</h2>
                <p className="text-sm text-gray-500 mt-1">Read carefully and find the answer using the available tools</p>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-gray-800 text-sm leading-relaxed prose prose-sm max-w-none prose-p:my-2 prose-strong:text-gray-900">
                <ReactMarkdown>
                  {currentTask.task_description}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Step-by-Step Tutorial Guide - Only for tutorial tasks when started */}
        {currentTask.is_tutorial && isCurrentTaskStarted && !isCurrentTaskCompleted && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border-2 border-green-300 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">📋</span>
              <h2 className="text-lg font-bold text-green-900">Step-by-Step Guide</h2>
              <span className="text-xs bg-green-200 text-green-800 px-2 py-1 rounded-full font-medium">Follow these steps</span>
            </div>

            <div className="space-y-4">
              {/* Step 1 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">1</div>
                <div>
                  <p className="font-semibold text-gray-900">Go to the Dashboards section</p>
                  <p className="text-sm text-gray-600 mt-1">
                    In the left sidebar, find the <strong>Dashboards</strong> section and click on <strong>"Production & Inventory"</strong>.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">2</div>
                <div>
                  <p className="font-semibold text-gray-900">Find the "Low Stock Alerts" table</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Scroll down on the Production & Inventory dashboard until you see the <strong>"Low Stock Alerts"</strong> table. It shows products with stock below 50 units.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">3</div>
                <div>
                  <p className="font-semibold text-gray-900">Count the low-stock products and identify the top category</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Look at the table — you will see <strong>4 products</strong> with low stock. Check the <strong>CATEGORY</strong> column for each product. You will notice that <strong>3 out of 4</strong> products belong to the <strong>"Clothing"</strong> category.
                  </p>
                </div>
              </div>

              {/* Step 4 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">4</div>
                <div>
                  <p className="font-semibold text-gray-900">Come back and write your answer</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Navigate back to this task page using the <strong>"Continue Task"</strong> button on the floating widget (bottom-right corner), or click <strong>"My Tasks"</strong> in the sidebar. Then type your answer in the <strong>"Your Answer"</strong> box below, for example:
                  </p>
                  <div className="mt-2 bg-white border border-green-200 rounded-lg p-3 text-sm text-gray-700 italic">
                    "There are 4 products with low stock (below 50 units). The category with the most low-stock items is Clothing, with 3 products."
                  </div>
                </div>
              </div>

              {/* Step 5 */}
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">5</div>
                <div>
                  <p className="font-semibold text-gray-900">Rate and submit</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Select a rating for <strong>"How difficult was this task?"</strong> and <strong>"How confident are you in your answer?"</strong>, then click the green <strong>"Submit Answer"</strong> button to move to the next task.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Available Tools Hint - Only when in progress */}
        {isCurrentTaskStarted && !isCurrentTaskCompleted && (
          <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
            <h3 className="font-medium text-blue-900 mb-2">Available Tools</h3>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-blue-200">
                <BarChart3 className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-blue-800">Dashboards</span>
              </div>
              {participant?.condition_assigned === "experimental" && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-blue-200">
                  <MessageSquare className="w-4 h-4 text-blue-600" />
                  <span className="text-sm text-blue-800">AI Chatbot</span>
                </div>
              )}
            </div>
            <p className="text-sm text-blue-700 mt-2">
              Use the sidebar navigation to access dashboards
              {participant?.condition_assigned === "experimental" && " and the AI chatbot"}.
              Your timer will continue running while you explore.
            </p>
          </div>
        )}

        {/* Auto-starting task - show loading */}
        {!isCurrentTaskStarted && !isCurrentTaskCompleted && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 shadow-sm text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600">Starting task...</p>
          </div>
        )}

        {/* Answer Submission Form (if started but not completed) */}
        {isCurrentTaskStarted && !isCurrentTaskCompleted && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Submit Your Answer</h3>

            {/* Answer Text Area */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Answer <span className="text-red-500">*</span>
              </label>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Enter your findings and answer here..."
                rows={6}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
              />
            </div>

            {/* Difficulty Rating */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                How difficult was this task? <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    onClick={() => setDifficultyRating(rating)}
                    className={`flex-1 py-3 px-2 rounded-lg border-2 transition-all text-center ${
                      difficultyRating === rating
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-200 hover:border-gray-300 text-gray-600"
                    }`}
                  >
                    <div className="font-semibold">{rating}</div>
                    <div className="text-xs mt-1">{difficultyLabels[rating - 1]}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Confidence Rating */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                How confident are you in your answer? <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((rating) => (
                  <button
                    key={rating}
                    onClick={() => setConfidenceRating(rating)}
                    className={`flex-1 py-3 px-2 rounded-lg border-2 transition-all text-center ${
                      confidenceRating === rating
                        ? "border-green-500 bg-green-50 text-green-700"
                        : "border-gray-200 hover:border-gray-300 text-gray-600"
                    }`}
                  >
                    <div className="font-semibold">{rating}</div>
                    <div className="text-xs mt-1">{confidenceLabels[rating - 1]}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Error Message */}
            {submitError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {submitError}
              </div>
            )}

            {/* Submit Button */}
            <button
              onClick={handleSubmitAnswer}
              disabled={submitting || !answer.trim()}
              className="w-full py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Send className="w-5 h-5" />
              {submitting ? "Submitting..." : "Submit Answer"}
            </button>
          </div>
        )}

        {/* Success Modal with Next Task Button */}
        {showSuccess && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-8 max-w-md mx-4 text-center shadow-2xl">
              <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Task Completed!</h3>
              <p className="text-gray-600 mb-6">
                Great job! Your answer has been recorded.
              </p>

              {/* Progress indicator - exclude tutorial from count */}
              <div className="bg-gray-100 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-600">
                  {currentTask.is_tutorial
                    ? 'Tutorial completed!'
                    : `${completedCount + (currentTask.is_tutorial ? 0 : 1)} of ${totalCount} tasks completed`
                  }
                </p>
                {!currentTask.is_tutorial && (
                  <div className="w-full bg-gray-300 rounded-full h-2 mt-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all"
                      style={{ width: `${((completedCount + 1) / totalCount) * 100}%` }}
                    />
                  </div>
                )}
              </div>

              <button
                onClick={handleNextTask}
                className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
              >
                {currentTask.is_tutorial ? (
                  <>
                    Start Real Tasks
                    <ArrowRight className="w-5 h-5" />
                  </>
                ) : completedCount + 1 < totalCount ? (
                  <>
                    Next Task
                    <ArrowRight className="w-5 h-5" />
                  </>
                ) : (
                  <>
                    Finish
                    <CheckCircle2 className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
