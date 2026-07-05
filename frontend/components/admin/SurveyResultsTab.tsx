"use client";

import dynamic from "next/dynamic";
import { useSurveyAnalytics } from "@/lib/hooks/useAdminData";
import type { LikertComparison, LikertStats } from "@/types/admin";

const BarChart = dynamic(() => import("recharts").then((m) => m.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((m) => m.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((m) => m.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((m) => m.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((m) => m.Tooltip), { ssr: false });
const Legend = dynamic(() => import("recharts").then((m) => m.Legend), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((m) => m.ResponsiveContainer), { ssr: false });

const CONTROL_COLOR = "#3b82f6";
const EXPERIMENTAL_COLOR = "#10b981";

const PRE_SURVEY_LABELS: Record<string, string> = {
  age: "Age",
  occupation_statuses: "Occupation Status",
  field_of_work: "Field of Work",
  field_of_study: "Field of Study",
  visual_analytics_frequency: "Visual Analytics Frequency",
  business_background: "Business Background",
  llm_chatbot_experience: "LLM/Chatbot Experience",
  bi_tools_experience: "BI Tools Experience",
};

const SECTION_A_LABELS: Record<string, string> = {
  // PU (A1-A4)
  dashboard_usefulness: "A1: Dashboard Usefulness (PU)",
  dashboard_performance: "A2: Improved Performance (PU)",
  dashboard_effectiveness: "A3: Enhanced Effectiveness (PU)",
  dashboard_productivity: "A4: Increased Productivity (PU)",
  // PEOU (A5-A8)
  dashboard_clear_understandable: "A5: Clear & Understandable (PEOU)",
  dashboard_easy_to_use: "A6: Easy to Use (PEOU)",
  dashboard_easy_to_control: "A7: Easy to Control (PEOU)",
  dashboard_low_mental_effort: "A8: Low Mental Effort (PEOU)",
  // Satisfaction (A9-A10)
  dashboard_satisfaction: "A9: Overall Satisfaction",
  dashboard_frustration: "A10: Frustrating to Use (R)",
};

const SECTION_B_LABELS: Record<string, string> = {
  // Part 1: Helpfulness (B1-B4)
  chatbot_helpfulness: "B1: Information Helpfulness",
  chatbot_easy_to_understand: "B2: Easy to Understand",
  chatbot_suitability: "B3: Accuracy & Relevance",
  chatbot_visualization_quality: "B4: Visualization Quality",
  // Part 2: Accuracy/Trust (B5-B8, frequency)
  chatbot_accuracy: "B5: Reacted Correctly (freq)",
  chatbot_correct_answers: "B6: Correct Answers (freq)",
  chatbot_reliance: "B7: Relied on Chatbot (freq)",
  chatbot_verification: "B8: Double-Checked (freq)",
  // Part 3: Intention (B9-B11)
  chatbot_future_use: "B9: Future Use Intention",
  chatbot_recommend: "B10: Would Recommend",
  chatbot_satisfaction: "B11: Overall Satisfaction",
};

const FEEDBACK_TYPE_LABELS: Record<string, string> = {
  general: "General Feedback (C1)",
  chatbot_liked: "What They Liked (C2)",
  chatbot_improvements: "Suggested Improvements (C3)",
};

export default function SurveyResultsTab() {
  const { data, loading, error } = useSurveyAnalytics();

  if (loading) return <div className="p-6 text-center text-gray-500">Loading survey analytics...</div>;
  if (error) return <div className="p-6 text-center text-red-500">{error}</div>;
  if (!data) return <div className="p-6 text-center text-gray-500">No survey data available</div>;

  return (
    <div className="space-y-8">
      {/* Pre-Survey Demographics */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pre-Survey Demographics</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(data.pre_survey).map(([field, distribution]) => (
            <div key={field} className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">{PRE_SURVEY_LABELS[field] || field}</h3>
              {distribution.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(180, distribution.length * 35)}>
                  <BarChart data={distribution} layout="vertical" barGap={2}>
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis dataKey="value" type="category" tick={{ fontSize: 11 }} width={120} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="control" name="Control" fill={CONTROL_COLOR} radius={[0, 4, 4, 0]} />
                    <Bar dataKey="experimental" name="Experimental" fill={EXPERIMENTAL_COLOR} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-gray-400">No data</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Post-Survey Section A: Dashboard Experience */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Section A: Dashboard Experience (Control vs Experimental)</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(data.post_survey.common).map(([field, stats]) => (
            <LikertComparisonCard key={field} label={SECTION_A_LABELS[field] || field} stats={stats as LikertComparison} />
          ))}
        </div>
      </section>

      {/* Post-Survey Section B: AI Chatbot Experience */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Section B: AI Chatbot Experience (Experimental Only)</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(data.post_survey.experimental_only).map(([field, stats]) => (
            <LikertStatsCard key={field} label={SECTION_B_LABELS[field] || field} stats={stats as LikertStats} />
          ))}
        </div>
      </section>

      {/* Open Feedback */}
      {data.post_survey.open_feedback.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Section C: Open Feedback</h2>
          <div className="space-y-3">
            {data.post_survey.open_feedback.map((fb, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-gray-500">{fb.participant_code}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${fb.condition === "control" ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"}`}>
                    {fb.condition}
                  </span>
                  {fb.type && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                      {FEEDBACK_TYPE_LABELS[fb.type] || fb.type}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-700">{fb.feedback}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function LikertComparisonCard({ label, stats }: { label: string; stats: LikertComparison }) {
  const chartData = [1, 2, 3, 4, 5].map((val, i) => ({
    rating: String(val),
    Control: stats.control_dist[i] || 0,
    Experimental: stats.experimental_dist[i] || 0,
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">{label}</h3>
      <div className="flex gap-4 mb-3 text-xs text-gray-500">
        <span>Control avg: <strong className="text-blue-600">{stats.control_avg?.toFixed(2) ?? "N/A"}</strong></span>
        <span>Experimental avg: <strong className="text-green-600">{stats.experimental_avg?.toFixed(2) ?? "N/A"}</strong></span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} barGap={2}>
          <XAxis dataKey="rating" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="Control" fill={CONTROL_COLOR} radius={[4, 4, 0, 0]} />
          <Bar dataKey="Experimental" fill={EXPERIMENTAL_COLOR} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function LikertStatsCard({ label, stats }: { label: string; stats: LikertStats }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{label}</h3>
      <p className="text-2xl font-bold text-gray-900">{stats.avg?.toFixed(2) ?? "N/A"}</p>
      <p className="text-xs text-gray-400 mb-2">avg (1-5)</p>
      <div className="flex gap-1">
        {(stats.distribution || []).map((count: number, i: number) => (
          <div key={i} className="flex-1 text-center">
            <div className="bg-purple-100 rounded text-xs font-medium text-purple-800 py-1">{count}</div>
            <div className="text-[10px] text-gray-400 mt-0.5">{i + 1}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
