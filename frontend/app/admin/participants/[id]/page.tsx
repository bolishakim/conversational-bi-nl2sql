"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import {
  useAdminParticipantDetail,
  useAdminParticipantInteractions,
  useAdminParticipantAnalytics
} from "@/lib/hooks/useAdminData";
import { api } from "@/lib/api";
import { ArrowLeft, User, Clock, Activity, RefreshCw, Shield, UserX, UserCheck, Shuffle, RotateCcw } from "lucide-react";

type AdminAction = "exclude" | "withdraw" | "reassign" | "reinstate" | null;

export default function ParticipantDetailPage() {
  const router = useRouter();
  const params = useParams();
  const participantId = params?.id as string;

  const [activeTab, setActiveTab] = useState<"overview" | "interactions" | "analytics">("overview");
  const [action, setAction] = useState<AdminAction>(null);
  const [actionReason, setActionReason] = useState("");
  const [reassignTarget, setReassignTarget] = useState<"control" | "experimental">("control");
  const [actionBusy, setActionBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { participant, loading: detailLoading, error: detailError, refresh: refreshDetail } = useAdminParticipantDetail(participantId);
  const { interactions, total: totalInteractions, loading: interactionsLoading, refresh: refreshInteractions } = useAdminParticipantInteractions(participantId);
  const { analytics, loading: analyticsLoading, refresh: refreshAnalytics } = useAdminParticipantAnalytics(participantId);

  // Check admin access on mount
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const user = await api.me();
        if (!user.can_access_admin) {
          router.push("/dashboards/sales");
        }
      } catch (error) {
        console.error("Failed to check admin access:", error);
        router.push("/login");
      }
    };
    checkAccess();
  }, [router]);

  if (detailLoading) {
    return (
      <AuthenticatedLayout
        title="Participant Details"
        subtitle="Loading participant information..."
      >
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-gray-600 mt-3">Loading participant data...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (detailError || !participant) {
    return (
      <AuthenticatedLayout
        title="Participant Details"
        subtitle="Error loading participant"
      >
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <p className="text-red-600 font-medium">{detailError || "Participant not found"}</p>
            <button
              onClick={() => router.push("/admin")}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Back to Admin Dashboard
            </button>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const getConditionBadge = (condition: string) => {
    const isControl = condition === "control";
    return (
      <span
        className={`px-3 py-1 rounded-full text-sm font-medium ${
          isControl
            ? "bg-blue-100 text-blue-800"
            : "bg-purple-100 text-purple-800"
        }`}
      >
        {isControl ? "Control Group" : "Experimental Group"}
      </span>
    );
  };

  const formatDuration = (minutes: number | null) => {
    if (minutes === null) return "N/A";
    if (minutes < 60) return `${Math.round(minutes)} minutes`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  return (
    <AuthenticatedLayout
      title={`Participant ${participant.participant_code}`}
      subtitle="Detailed tracking and analytics"
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.push("/admin")}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Admin Dashboard</span>
          </button>
          <button
            onClick={() => {
              refreshDetail();
              refreshInteractions();
              refreshAnalytics();
            }}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="text-sm font-medium">Refresh</span>
          </button>
        </div>

        {/* Participant Info */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full">
                <User className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {participant.participant_code}
                </h2>
                <p className="text-gray-600">
                  {participant.occupation_statuses || participant.occupation_status || "N/A"} • {participant.field_of_work || participant.field_of_study || "N/A"}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Status: <span className="font-medium text-gray-700 capitalize">{participant.status}</span>
                  {participant.exclusion_reason ? <> • {participant.exclusion_reason}</> : null}
                </p>
              </div>
            </div>
            {getConditionBadge(participant.condition_assigned)}
          </div>
        </div>

        {/* Admin Actions */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Admin actions</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => { setAction("exclude"); setActionReason(""); setActionError(null); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 rounded-md"
              >
                <UserX className="w-3.5 h-3.5" /> Exclude
              </button>
              <button
                onClick={() => { setAction("withdraw"); setActionReason(""); setActionError(null); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-md"
              >
                <UserX className="w-3.5 h-3.5" /> Withdraw
              </button>
              <button
                onClick={() => {
                  setAction("reassign");
                  setActionReason("");
                  setActionError(null);
                  setReassignTarget(participant.condition_assigned === "control" ? "experimental" : "control");
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-md"
              >
                <Shuffle className="w-3.5 h-3.5" /> Reassign condition
              </button>
              {(participant.status === "excluded" || participant.status === "withdrawn") && (
                <button
                  onClick={() => { setAction("reinstate"); setActionError(null); }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 rounded-md"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Reinstate
                </button>
              )}
            </div>
          </div>
          {participant.admin_notes ? (
            <pre className="mt-3 p-3 text-xs text-gray-600 bg-gray-50 rounded border border-gray-100 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
              {participant.admin_notes}
            </pre>
          ) : null}
        </div>

        {/* Action Modal */}
        {action && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {action === "exclude" && "Exclude participant from analysis"}
                {action === "withdraw" && "Record participant withdrawal"}
                {action === "reassign" && "Reassign participant condition"}
                {action === "reinstate" && "Reinstate participant"}
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                {action === "exclude" && "Participant data is kept but dropped from all analytics aggregates. Reversible."}
                {action === "withdraw" && "Records the participant's withdrawal request with a timestamp. Reversible."}
                {action === "reassign" && "Post-hoc condition change; marked as assignment_method='manual_override'. Breaks randomization -- note this in your methods section."}
                {action === "reinstate" && "Restores the participant's status so they count in analytics again."}
              </p>

              {action === "reassign" && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Move to condition</label>
                  <select
                    value={reassignTarget}
                    onChange={(e) => setReassignTarget(e.target.value as "control" | "experimental")}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="control">control</option>
                    <option value="experimental">experimental</option>
                  </select>
                </div>
              )}

              {action !== "reinstate" && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Reason {action === "withdraw" ? "(optional)" : "*"}
                  </label>
                  <textarea
                    value={actionReason}
                    onChange={(e) => setActionReason(e.target.value)}
                    rows={3}
                    placeholder="Short explanation for the audit trail..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              {actionError && (
                <div className="mb-3 p-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded">
                  {actionError}
                </div>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setAction(null); setActionError(null); }}
                  disabled={actionBusy}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    setActionError(null);
                    if (action !== "reinstate" && action !== "withdraw" && !actionReason.trim()) {
                      setActionError("Reason is required.");
                      return;
                    }
                    setActionBusy(true);
                    try {
                      if (action === "exclude") await api.adminExcludeParticipant(participantId, actionReason.trim());
                      else if (action === "withdraw") await api.adminWithdrawParticipant(participantId, actionReason.trim() || undefined);
                      else if (action === "reassign") await api.adminReassignCondition(participantId, reassignTarget, actionReason.trim());
                      else if (action === "reinstate") await api.adminReinstateParticipant(participantId);
                      await refreshDetail();
                      setAction(null);
                      setActionReason("");
                    } catch (e: any) {
                      setActionError(e?.message || "Action failed.");
                    } finally {
                      setActionBusy(false);
                    }
                  }}
                  disabled={actionBusy}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
                >
                  {actionBusy ? "Working..." : "Confirm"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* KPI Cards - Compact Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-gray-600">Tasks Completed</h3>
              <Activity className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {participant.tasks_completed}/{participant.tasks_total}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {((participant.tasks_completed / participant.tasks_total) * 100).toFixed(0)}% complete
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-gray-600">Session Duration</h3>
              <Clock className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {formatDuration(participant.session_duration_minutes)}
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-medium text-gray-600">Total Interactions</h3>
              <Activity className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{totalInteractions}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="border-b border-gray-200">
            <nav className="flex gap-8 px-6" aria-label="Tabs">
              <button
                onClick={() => setActiveTab("overview")}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === "overview"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab("interactions")}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === "interactions"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                Interactions ({totalInteractions})
              </button>
              <button
                onClick={() => setActiveTab("analytics")}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === "analytics"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                Analytics
              </button>
            </nav>
          </div>

          <div className="p-6">
            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Pre-Survey Information
                  </h3>
                  <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Age</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.age || participant.age_range || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Occupation Status</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.occupation_statuses || participant.occupation_status || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Field of Work</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.field_of_work || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Field of Study</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.field_of_study || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Visual Analytics Frequency</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.visual_analytics_frequency || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Business Background</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.business_background || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">LLM Chatbot Experience</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.llm_chatbot_experience || "N/A"}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-gray-500">BI Tools Experience</dt>
                      <dd className="mt-1 text-sm text-gray-900">{participant.bi_tools_experience || "N/A"}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            )}

            {/* Interactions Tab */}
            {activeTab === "interactions" && (
              <div>
                {interactionsLoading ? (
                  <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : interactions.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-gray-500">No interactions logged yet</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Task</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {interactions.map((interaction) => (
                          <tr key={interaction.id}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {interaction.interaction_sequence}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(interaction.interaction_timestamp).toLocaleTimeString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {interaction.interaction_type}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              Task {interaction.task_number}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900">
                              {interaction.query_text || interaction.dashboard_element || "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Analytics Tab */}
            {activeTab === "analytics" && (
              <div>
                {analyticsLoading ? (
                  <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : !analytics ? (
                  <div className="text-center py-12">
                    <p className="text-gray-500">No analytics data available</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Interactions by Type */}
                    {analytics.interactions_by_type.length > 0 && (
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-3">Interactions by Type</h4>
                        <div className="space-y-2">
                          {analytics.interactions_by_type.map((item) => (
                            <div key={item.type} className="flex items-center justify-between">
                              <span className="text-sm text-gray-700">{item.type}</span>
                              <span className="text-sm font-medium text-gray-900">{item.count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Dashboard Elements Clicked */}
                    {analytics.dashboard_elements_clicked.length > 0 && (
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-3">Dashboard Elements Clicked</h4>
                        <div className="space-y-2">
                          {analytics.dashboard_elements_clicked.slice(0, 10).map((item) => (
                            <div key={item.element} className="flex items-center justify-between">
                              <span className="text-sm text-gray-700">{item.element}</span>
                              <span className="text-sm font-medium text-gray-900">{item.count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Task Durations */}
                    {analytics.task_durations.length > 0 && (
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-3">Task Durations</h4>
                        <div className="space-y-2">
                          {analytics.task_durations.map((item) => (
                            <div key={item.task_number} className="flex items-center justify-between">
                              <span className="text-sm text-gray-700">Task {item.task_number}</span>
                              <span className="text-sm font-medium text-gray-900">
                                {Math.round(item.duration_seconds / 60)}m
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}
