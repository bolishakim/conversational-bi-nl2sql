"use client";

import { useState } from "react";
import { useTaskSession } from "@/contexts/TaskSessionContext";
import { X, ChevronUp, ChevronDown, Clock, CheckCircle2, FileText, Play, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";

interface TaskOverlayProps {
  onClose?: () => void;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function TaskOverlay({ onClose }: TaskOverlayProps) {
  const router = useRouter();
  const [isMinimized, setIsMinimized] = useState(false);
  const [starting, setStarting] = useState(false);
  const {
    currentTask,
    elapsedSeconds,
    isCurrentTaskStarted,
    isCurrentTaskCompleted,
    completedCount,
    totalCount,
    allTasksCompleted,
    startSession,
  } = useTaskSession();

  // Don't show if no current task or all tasks completed
  if (!currentTask || allTasksCompleted) {
    return null;
  }

  // Minimized view
  if (isMinimized) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsMinimized(false)}
          className="bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg hover:bg-blue-700 transition-all flex items-center gap-2 group"
        >
          <FileText className="w-5 h-5" />
          <span className="font-medium">
            {currentTask.is_tutorial ? 'Tutorial' : `Task ${currentTask.task_number}/${totalCount}`}
          </span>
          {isCurrentTaskStarted && !currentTask.is_tutorial && (
            <span className="text-xs bg-blue-500 px-2 py-1 rounded">
              {formatDuration(elapsedSeconds)}
            </span>
          )}
          <ChevronUp className="w-4 h-4 ml-1 group-hover:translate-y-[-2px] transition-transform" />
        </button>
      </div>
    );
  }

  // Full view
  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-t-lg flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          <h3 className="font-semibold">
            {currentTask.is_tutorial ? 'Tutorial Task' : `Task ${currentTask.task_number} of ${totalCount}`}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMinimized(true)}
            className="hover:bg-blue-600 p-1 rounded transition-colors"
            title="Minimize"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="hover:bg-blue-600 p-1 rounded transition-colors"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isCurrentTaskCompleted ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="w-5 h-5" />
                <span className="text-sm font-medium">Completed</span>
              </div>
            ) : isCurrentTaskStarted ? (
              <div className="flex items-center gap-2 text-yellow-600">
                <Clock className="w-5 h-5" />
                <span className="text-sm font-medium">In Progress</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-gray-500">
                <Clock className="w-5 h-5" />
                <span className="text-sm font-medium">Not Started</span>
              </div>
            )}
          </div>

          {/* Timer */}
          {isCurrentTaskStarted && !currentTask.is_tutorial && (
            <div className="flex items-center gap-2 bg-gray-100 px-3 py-1 rounded-full">
              <Clock className="w-4 h-4 text-gray-600" />
              <span className="font-mono text-sm font-medium text-gray-800">
                {formatDuration(elapsedSeconds)}
              </span>
            </div>
          )}
        </div>

        {/* Tutorial Badge */}
        {currentTask.is_tutorial && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center gap-2 text-blue-800">
              <span className="text-lg">🎓</span>
              <span className="text-sm font-medium">Practice Task (Not Scored)</span>
            </div>
          </div>
        )}

        {/* Task Description */}
        {isCurrentTaskStarted && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase">Task Description</h4>
            <div className="text-sm text-gray-700 prose prose-sm max-w-none">
              <ReactMarkdown>
                {currentTask.task_description}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Tutorial Steps - Brief guide for tutorial task */}
        {currentTask.is_tutorial && isCurrentTaskStarted && !isCurrentTaskCompleted && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <h4 className="text-xs font-semibold text-green-800 mb-2 uppercase flex items-center gap-1">
              📋 How to solve this
            </h4>
            <ol className="text-xs text-green-900 space-y-1.5 list-none">
              <li className="flex gap-2">
                <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">1</span>
                <span>Go to <strong>Production & Inventory</strong> dashboard</span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">2</span>
                <span>Scroll to the <strong>"Low Stock Alerts"</strong> table</span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">3</span>
                <span>Count products & check categories → <strong>4 products</strong>, most are <strong>Clothing (3)</strong></span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">4</span>
                <span>Click <strong>"Continue Task"</strong> below → write your answer & submit</span>
              </li>
            </ol>
          </div>
        )}

        {/* Progress */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-700 uppercase">Progress</span>
            <span className="text-sm font-medium text-gray-800">
              {completedCount}/{totalCount}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
            />
          </div>
        </div>

        {/* Domain */}
        {currentTask.domain && (
          <div className="text-xs text-gray-500">
            <span className="font-medium">Domain:</span> {currentTask.domain}
          </div>
        )}
      </div>

      {/* Action Button + Footer */}
      <div className="border-t border-gray-200 px-4 py-3 bg-gray-50 rounded-b-lg space-y-2">
        {!isCurrentTaskCompleted && (
          <button
            disabled={starting}
            onClick={async () => {
              if (isCurrentTaskStarted) {
                router.push(`/tasks/${currentTask.id}`);
              } else {
                setStarting(true);
                try {
                  await startSession();
                  if (currentTask) {
                    router.push(`/tasks/${currentTask.id}`);
                  }
                } finally {
                  setStarting(false);
                }
              }
            }}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-semibold text-sm transition-colors ${
              isCurrentTaskStarted
                ? "bg-yellow-500 hover:bg-yellow-600 text-white"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            } ${starting ? "opacity-70 cursor-not-allowed" : ""}`}
          >
            {isCurrentTaskStarted ? (
              <>
                <ArrowRight className="w-4 h-4" />
                Continue Task
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                {starting ? "Starting..." : "Start Tasks"}
              </>
            )}
          </button>
        )}
        <p className="text-xs text-gray-600 text-center">
          Use dashboards and tools to find the answer
        </p>
      </div>
    </div>
  );
}
