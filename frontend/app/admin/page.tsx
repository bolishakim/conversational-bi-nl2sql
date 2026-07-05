"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import AuthenticatedLayout from "@/components/AuthenticatedLayout";
import ParticipantList from "@/components/admin/ParticipantList";
import { useAdminParticipants, useStudyOverview } from "@/lib/hooks/useAdminData";
import { api } from "@/lib/api";
import { Users, UserCheck, Activity, RefreshCw, BarChart3, ClipboardList, MessageSquare, Download } from "lucide-react";

// Dynamic imports for tab components (code-split)
const TaskComparisonTab = dynamic(() => import("@/components/admin/TaskComparisonTab"), { ssr: false });
const SurveyResultsTab = dynamic(() => import("@/components/admin/SurveyResultsTab"), { ssr: false });
const ChatbotAnalyticsTab = dynamic(() => import("@/components/admin/ChatbotAnalyticsTab"), { ssr: false });
const DataExportTab = dynamic(() => import("@/components/admin/DataExportTab"), { ssr: false });

// Recharts for overview charts
const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const LineChart = dynamic(() => import("recharts").then((m) => m.LineChart), { ssr: false });
const Line = dynamic(() => import("recharts").then((m) => m.Line), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const Legend = dynamic(() => import("recharts").then((m) => m.Legend), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

const TABS = [
  { key: "overview", label: "Overview", icon: BarChart3 },
  { key: "tasks", label: "Task Performance", icon: ClipboardList },
  { key: "surveys", label: "Survey Results", icon: Users },
  { key: "chatbot", label: "Chatbot Analytics", icon: MessageSquare },
  { key: "export", label: "Data Export", icon: Download },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function AdminDashboardPage() {
  return (
    <Suspense fallback={
      <AuthenticatedLayout title="Admin Dashboard" subtitle="Participant tracking and analytics">
        <div className="flex items-center justify-center h-full">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </AuthenticatedLayout>
    }>
      <AdminDashboard />
    </Suspense>
  );
}

function AdminDashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<TabKey>((searchParams.get("tab") as TabKey) || "overview");
  const { participants, loading, error, refresh } = useAdminParticipants();

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

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", tab);
    window.history.replaceState({}, "", url.toString());
  };

  if (loading && activeTab === "overview") {
    return (
      <AuthenticatedLayout title="Admin Dashboard" subtitle="Participant tracking and analytics">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-gray-600 mt-3">Loading...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout title="Admin Dashboard" subtitle="Participant tracking and analytics">
      <div className="p-6 space-y-6">
        {/* Header with Refresh + Tab Navigation */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Experiment Analytics</h1>
          <button
            onClick={() => refresh()}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="text-sm font-medium">Refresh</span>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-1 -mb-px overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => handleTabChange(tab.key)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && <OverviewTab participants={participants} error={error} />}
        {activeTab === "tasks" && <TaskComparisonTab />}
        {activeTab === "surveys" && <SurveyResultsTab />}
        {activeTab === "chatbot" && <ChatbotAnalyticsTab />}
        {activeTab === "export" && <DataExportTab />}
      </div>
    </AuthenticatedLayout>
  );
}

// Overview tab (existing content + new charts)
// Participants with these statuses are excluded from analytics aggregates
// but still visible in the Participant Tracking list.
const ANALYSIS_EXCLUDED_STATUSES = new Set(["excluded", "withdrawn"]);

function OverviewTab({ participants, error }: { participants: any[]; error: string | null }) {
  const { data: overview } = useStudyOverview();

  if (error) {
    return <div className="text-center text-red-500 py-8">{error}</div>;
  }

  // Only count participants eligible for analysis.
  const analysisParticipants = participants.filter(
    (p) => !ANALYSIS_EXCLUDED_STATUSES.has(p.status)
  );
  const totalParticipants = analysisParticipants.length;
  const excludedCount = participants.length - totalParticipants;
  const controlCount = analysisParticipants.filter((p) => p.condition_assigned === "control").length;
  const experimentalCount = analysisParticipants.filter((p) => p.condition_assigned === "experimental").length;

  const activeParticipants = analysisParticipants.filter((p) => {
    if (!p.last_activity) return false;
    const diffMinutes = (Date.now() - new Date(p.last_activity).getTime()) / (1000 * 60);
    return diffMinutes < 30;
  }).length;

  const completedParticipants = analysisParticipants.filter(
    (p) => p.tasks_completed === p.tasks_total && p.tasks_total > 0
  ).length;

  const avgCompletion = totalParticipants > 0
    ? analysisParticipants.reduce((sum: number, p: any) => sum + p.tasks_completed, 0) / totalParticipants
    : 0;

  // Recruitment source split over the analysis-eligible subset
  const prolificCount = analysisParticipants.filter(
    (p: any) => p.recruitment_source === "prolific"
  ).length;
  const universityCount = totalParticipants - prolificCount;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard
          label="Total Participants"
          value={totalParticipants}
          icon={<Users className="w-4 h-4 text-gray-400" />}
          sub={excludedCount > 0 ? `${excludedCount} excluded / withdrawn` : undefined}
        />
        <KPICard
          label="Control Group"
          value={controlCount}
          icon={<UserCheck className="w-4 h-4 text-gray-400" />}
          sub={totalParticipants > 0 ? `${((controlCount / totalParticipants) * 100).toFixed(0)}% of total` : undefined}
        />
        <KPICard
          label="Experimental Group"
          value={experimentalCount}
          icon={<UserCheck className="w-4 h-4 text-gray-400" />}
          sub={totalParticipants > 0 ? `${((experimentalCount / totalParticipants) * 100).toFixed(0)}% of total` : undefined}
        />
        <KPICard label="Active Now" value={activeParticipants} icon={<Activity className="w-4 h-4 text-gray-400" />} sub="Last 30 minutes" />
        <KPICard
          label="Completed Sessions"
          value={completedParticipants}
          icon={<Activity className="w-4 h-4 text-gray-400" />}
          sub={totalParticipants > 0 ? `${((completedParticipants / totalParticipants) * 100).toFixed(0)}% rate` : undefined}
        />
        <KPICard label="Avg Tasks Done" value={avgCompletion.toFixed(1)} icon={<Activity className="w-4 h-4 text-gray-400" />} sub="Per participant" />
        <KPICard
          label="University"
          value={universityCount}
          icon={<Users className="w-4 h-4 text-gray-400" />}
          sub={totalParticipants > 0 ? `${((universityCount / totalParticipants) * 100).toFixed(0)}% of total` : undefined}
        />
        <KPICard
          label="Prolific"
          value={prolificCount}
          icon={<Users className="w-4 h-4 text-gray-400" />}
          sub={totalParticipants > 0 ? `${((prolificCount / totalParticipants) * 100).toFixed(0)}% of total` : undefined}
        />
      </div>

      {/* Charts Row */}
      {overview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Enrollment Timeline */}
          {overview.enrollment_over_time.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Enrollment Timeline</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={overview.enrollment_over_time}>
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="cumulative" name="Cumulative" stroke="#6366f1" strokeWidth={2} />
                  <Line type="monotone" dataKey="control" name="Control" stroke="#3b82f6" strokeDasharray="5 5" />
                  <Line type="monotone" dataKey="experimental" name="Experimental" stroke="#10b981" strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Completion Funnel */}
          {overview.completion_funnel.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Completion Funnel</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={overview.completion_funnel} margin={{ top: 5, right: 20, bottom: 40, left: 0 }}>
                  <XAxis dataKey="stage" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" interval={0} height={60} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Additional overview KPIs from overview endpoint */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <KPICard label="Completion Rate" value={`${overview.completion_rate_percent}%`} />
          <KPICard label="Avg Session Duration" value={overview.avg_session_duration_minutes ? `${overview.avg_session_duration_minutes} min` : "N/A"} />
          <KPICard label="Surveys Completed" value={overview.survey_completed_count} />
        </div>
      )}

      {/* Participant List */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">All Participants</h2>
          <p className="text-sm text-gray-600 mt-1">Click on a participant to view detailed tracking information</p>
        </div>
        <div className="p-6">
          <ParticipantList participants={participants} />
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, icon, sub }: { label: string; value: string | number; icon?: React.ReactNode; sub?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-gray-600">{label}</h3>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}
