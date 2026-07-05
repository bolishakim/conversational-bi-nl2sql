"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";
import Button from "@/components/Button";
import { CheckCircle2 } from "lucide-react";

type SurveyStep = "loading" | "survey" | "success";

// Prolific completion codes per condition. Generated in the Prolific dashboard
// when each study is created and must match those studies exactly. Both studies
// currently share the same code because the experimental study was duplicated
// from control (Prolific copies the completion code on duplicate). Prolific
// validates per-study using session_id, so shared codes work correctly. If you
// rotate one code in the Prolific UI, update the matching entry here.
const PROLIFIC_COMPLETION_CODES: Record<string, string> = {
  control: "C2DATA07",
  experimental: "C2DATA07",
};

const LIKERT_OPTIONS = [
  { value: 1, short: "Strongly Disagree" },
  { value: 2, short: "Disagree" },
  { value: 3, short: "Neutral" },
  { value: 4, short: "Agree" },
  { value: 5, short: "Strongly Agree" },
];

const FREQUENCY_OPTIONS = [
  { value: 1, short: "Never" },
  { value: 2, short: "Rarely" },
  { value: 3, short: "Sometimes" },
  { value: 4, short: "Often" },
  { value: 5, short: "Always" },
];

export default function SurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState<SurveyStep>("loading");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [participantId, setParticipantId] = useState("");
  const [condition, setCondition] = useState<string | null>(null);

  // Section A: Perceived Usefulness (A1-A4)
  const [a1, setA1] = useState<number | null>(null);
  const [a2, setA2] = useState<number | null>(null);
  const [a3, setA3] = useState<number | null>(null);
  const [a4, setA4] = useState<number | null>(null);

  // Section A: Perceived Ease of Use (A5-A8)
  const [a5, setA5] = useState<number | null>(null);
  const [a6, setA6] = useState<number | null>(null);
  const [a7, setA7] = useState<number | null>(null);
  const [a8, setA8] = useState<number | null>(null);

  // Section A: User Satisfaction (A9-A10)
  const [a9, setA9] = useState<number | null>(null);
  const [a10, setA10] = useState<number | null>(null);

  // Section B Part 1: Helpfulness & Understanding (B1-B4, Likert)
  const [b1, setB1] = useState<number | null>(null);
  const [b2, setB2] = useState<number | null>(null);
  const [b3, setB3] = useState<number | null>(null);
  const [b4, setB4] = useState<number | null>(null);

  // Section B Part 2: Accuracy, Trust & Behavior (B5-B8, Frequency)
  const [b5, setB5] = useState<number | null>(null);
  const [b6, setB6] = useState<number | null>(null);
  const [b7, setB7] = useState<number | null>(null);
  const [b8, setB8] = useState<number | null>(null);

  // Section B Part 3: Future Use Intention (B9-B11, Likert)
  const [b9, setB9] = useState<number | null>(null);
  const [b10, setB10] = useState<number | null>(null);
  const [b11, setB11] = useState<number | null>(null);

  // Section C: Open Feedback
  const [c1, setC1] = useState("");
  const [c2, setC2] = useState("");
  const [c3, setC3] = useState("");

  useEffect(() => {
    if (!auth.getToken()) {
      router.push("/login");
      return;
    }
    loadParticipantInfo();
  }, []);

  const loadParticipantInfo = async () => {
    try {
      const info = await api.getMyParticipantInfo();
      if (!info.enrolled) {
        router.push("/onboarding");
        return;
      }
      setParticipantId(info.id);
      setCondition(info.condition_assigned);

      if (info.post_study_survey_responses && Object.keys(info.post_study_survey_responses).length > 0) {
        setStep("success");
        return;
      }

      setStep("survey");
    } catch (err: any) {
      console.error("Error loading participant info:", err);
      setError(err.message || "Failed to load participant info");
      setStep("survey");
    }
  };

  const isExperimental = condition === "experimental";

  const isFormComplete = () => {
    const sectionA = a1 !== null && a2 !== null && a3 !== null && a4 !== null &&
                     a5 !== null && a6 !== null && a7 !== null && a8 !== null &&
                     a9 !== null && a10 !== null;

    if (!isExperimental) return sectionA;

    return sectionA &&
      b1 !== null && b2 !== null && b3 !== null && b4 !== null &&
      b5 !== null && b6 !== null && b7 !== null && b8 !== null &&
      b9 !== null && b10 !== null && b11 !== null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const surveyResponses: Record<string, any> = {
        // Section A: PU
        dashboard_usefulness: a1,
        dashboard_performance: a2,
        dashboard_effectiveness: a3,
        dashboard_productivity: a4,
        // Section A: PEOU
        dashboard_clear_understandable: a5,
        dashboard_easy_to_use: a6,
        dashboard_easy_to_control: a7,
        dashboard_low_mental_effort: a8,
        // Section A: Satisfaction
        dashboard_satisfaction: a9,
        dashboard_frustration: a10,
        // Section C
        open_feedback: c1,
      };

      if (isExperimental) {
        // Section B Part 1
        surveyResponses.chatbot_helpfulness = b1;
        surveyResponses.chatbot_easy_to_understand = b2;
        surveyResponses.chatbot_suitability = b3;
        surveyResponses.chatbot_visualization_quality = b4;
        // Section B Part 2 (frequency)
        surveyResponses.chatbot_accuracy = b5;
        surveyResponses.chatbot_correct_answers = b6;
        surveyResponses.chatbot_reliance = b7;
        surveyResponses.chatbot_verification = b8;
        // Section B Part 3
        surveyResponses.chatbot_future_use = b9;
        surveyResponses.chatbot_recommend = b10;
        surveyResponses.chatbot_satisfaction = b11;
        // Section C experimental
        surveyResponses.chatbot_liked = c2;
        surveyResponses.chatbot_improvements = c3;
      }

      await api.submitPostStudySurvey(participantId, surveyResponses);
      setStep("success");
    } catch (err: any) {
      console.error("Survey submission error:", err);
      setError(err.message || "Failed to submit survey. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const renderLikertRow = (
    questionId: string,
    questionNumber: string,
    label: string,
    value: number | null,
    setter: (v: number) => void,
    options = LIKERT_OPTIONS
  ) => (
    <div className="py-4 border-b border-gray-100 last:border-b-0">
      <p className="text-[15px] font-semibold text-gray-800 mb-3">
        {questionNumber}. {label} <span className="text-red-500">*</span>
      </p>
      <div className="flex items-center justify-between gap-1">
        {options.map((option) => {
          const isSelected = value === option.value;
          return (
            <label
              key={option.value}
              className={`flex-1 text-center cursor-pointer rounded-lg border-2 py-2 px-1 transition-all ${
                isSelected
                  ? "border-blue-500 bg-blue-50 shadow-sm"
                  : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <input
                type="radio"
                name={questionId}
                value={option.value}
                checked={isSelected}
                onChange={() => setter(option.value)}
                className="sr-only"
              />
              <div className={`text-lg font-bold ${isSelected ? "text-blue-600" : "text-gray-400"}`}>
                {option.value}
              </div>
              <div className={`text-[10px] leading-tight mt-0.5 ${isSelected ? "text-blue-600 font-medium" : "text-gray-400"}`}>
                {option.short}
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );

  if (step === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">Loading survey...</p>
        </div>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6">
        <div className="w-full max-w-lg">
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Thank You!</h1>
            <p className="text-gray-600 mb-6">
              Your survey has been submitted successfully. Thank you for participating in this study.
            </p>
            <div className="bg-green-50 rounded-lg border border-green-200 p-4 mb-6">
              <p className="text-sm text-green-800">
                Your responses have been recorded. You may now close this window.
              </p>
              <p className="text-sm text-green-700 mt-2">
                Questions or feedback? Contact: <a href="mailto:bolis.hakim@student.tugraz.at" className="underline">bolis.hakim@student.tugraz.at</a>
              </p>
            </div>
            <Button
              onClick={async () => {
                try {
                  await api.logout();
                } catch {}
                auth.removeToken();
                const prolificPid = sessionStorage.getItem("PROLIFIC_PID");
                if (prolificPid) {
                  const code =
                    PROLIFIC_COMPLETION_CODES[condition ?? ""] ??
                    PROLIFIC_COMPLETION_CODES.control;
                  sessionStorage.removeItem("PROLIFIC_PID");
                  sessionStorage.removeItem("PROLIFIC_STUDY_ID");
                  sessionStorage.removeItem("PROLIFIC_SESSION_ID");
                  sessionStorage.removeItem("PROLIFIC_CONDITION");
                  sessionStorage.removeItem("PARTICIPANT_ID");
                  window.location.href = `https://app.prolific.com/submissions/complete?cc=${code}`;
                } else {
                  router.push("/login");
                }
              }}
              variant="primary"
              className="w-full"
            >
              Finish Study
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const sectionAValues = [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10];
  const sectionBValues = isExperimental ? [b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11] : [];
  const totalQuestions = isExperimental ? 21 : 10;
  const answeredCount = [...sectionAValues, ...sectionBValues].filter((v) => v !== null).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white px-6 py-8">
      <div className="w-full max-w-2xl mx-auto">
        {/* Sticky Header with Progress */}
        <div className="sticky top-0 z-10 bg-gradient-to-b from-blue-50 via-blue-50 to-transparent pb-4 -mx-6 px-6 pt-2">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900">Post-Study Survey</h1>
            <p className="text-gray-500 mt-1">Please share your experience. All responses are anonymous.</p>
            <div className="mt-3 flex items-center justify-center gap-3">
              <div className="flex-1 max-w-xs bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 font-medium">{answeredCount}/{totalQuestions}</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Section A: Perceived Usefulness */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
            <div className="bg-blue-50 border-b border-blue-200 rounded-t-xl px-5 py-3">
              <h2 className="text-base font-semibold text-blue-800">Section A: Dashboard Experience</h2>
              <p className="text-xs text-blue-500">Perceived Usefulness</p>
            </div>
            <div className="px-5">
              {renderLikertRow("a1", "A1", "I found the dashboard useful for completing the data analysis tasks.", a1, setA1)}
              {renderLikertRow("a2", "A2", "Using the dashboard improved my performance in the data analysis tasks.", a2, setA2)}
              {renderLikertRow("a3", "A3", "Using the dashboard enhanced my effectiveness in the data analysis tasks.", a3, setA3)}
              {renderLikertRow("a4", "A4", "Using the dashboard increased my productivity in the data analysis tasks.", a4, setA4)}
            </div>
          </div>

          {/* Section A: Perceived Ease of Use */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
            <div className="bg-blue-50 border-b border-blue-200 rounded-t-xl px-5 py-3">
              <h2 className="text-base font-semibold text-blue-800">Section A: Dashboard Experience</h2>
              <p className="text-xs text-blue-500">Perceived Ease of Use</p>
            </div>
            <div className="px-5">
              {renderLikertRow("a5", "A5", "My interaction with the dashboard was clear and understandable.", a5, setA5)}
              {renderLikertRow("a6", "A6", "I found the dashboard easy to use.", a6, setA6)}
              {renderLikertRow("a7", "A7", "I found it easy to get the dashboard to do what I wanted it to do.", a7, setA7)}
              {renderLikertRow("a8", "A8", "Interacting with the dashboard did not require a lot of my mental effort.", a8, setA8)}
            </div>
          </div>

          {/* Section A: User Satisfaction */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
            <div className="bg-blue-50 border-b border-blue-200 rounded-t-xl px-5 py-3">
              <h2 className="text-base font-semibold text-blue-800">Section A: Dashboard Experience</h2>
              <p className="text-xs text-blue-500">User Satisfaction</p>
            </div>
            <div className="px-5">
              {renderLikertRow("a9", "A9", "Overall, I am satisfied with the dashboard experience.", a9, setA9)}
              {renderLikertRow("a10", "A10", "I found the dashboard frustrating to use.", a10, setA10)}
            </div>
          </div>

          {/* Section B: AI Chatbot Experience */}
          {isExperimental && (
            <>
              {/* Part 1: Helpfulness & Understanding */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
                <div className="bg-purple-50 border-b border-purple-200 rounded-t-xl px-5 py-3">
                  <h2 className="text-base font-semibold text-purple-800">Section B: AI Chatbot Experience</h2>
                  <p className="text-xs text-purple-500">Part 1: Helpfulness & Ease of Understanding</p>
                </div>
                <div className="px-5">
                  {renderLikertRow("b1", "B1", "I found the information given by the chatbot helpful for solving the data analysis tasks.", b1, setB1)}
                  {renderLikertRow("b2", "B2", "I found the information given by the chatbot easy to understand.", b2, setB2)}
                  {renderLikertRow("b3", "B3", "I found the answers provided by the chatbot accurate and relevant to the data analysis tasks.", b3, setB3)}
                  {renderLikertRow("b4", "B4", "I found the visualizations (charts/graphs) generated by the chatbot clear and helpful for understanding the answers.", b4, setB4)}
                </div>
              </div>

              {/* Part 2: Accuracy, Trust & Behavior (Frequency scale) */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
                <div className="bg-purple-50 border-b border-purple-200 rounded-t-xl px-5 py-3">
                  <h2 className="text-base font-semibold text-purple-800">Section B: AI Chatbot Experience</h2>
                  <p className="text-xs text-purple-500">Part 2: Accuracy, Trust & Behavior</p>
                </div>
                <div className="bg-amber-50 border-b border-amber-200 px-5 py-2">
                  <p className="text-xs text-amber-700 font-medium">Response scale: Never - Rarely - Sometimes - Often - Always</p>
                </div>
                <div className="px-5">
                  {renderLikertRow("b5", "B5", "How often did the chatbot react correctly to your questions?", b5, setB5, FREQUENCY_OPTIONS)}
                  {renderLikertRow("b6", "B6", "How often do you think the chatbot gave correct answers for the data analysis tasks?", b6, setB6, FREQUENCY_OPTIONS)}
                  {renderLikertRow("b7", "B7", "How often did you rely only on the chatbot for solving the data analysis tasks?", b7, setB7, FREQUENCY_OPTIONS)}
                  {renderLikertRow("b8", "B8", "How often did you double-check the chatbot's answers on the dashboard?", b8, setB8, FREQUENCY_OPTIONS)}
                </div>
              </div>

              {/* Part 3: Future Use Intention */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
                <div className="bg-purple-50 border-b border-purple-200 rounded-t-xl px-5 py-3">
                  <h2 className="text-base font-semibold text-purple-800">Section B: AI Chatbot Experience</h2>
                  <p className="text-xs text-purple-500">Part 3: Future Use & Satisfaction</p>
                </div>
                <div className="px-5">
                  {renderLikertRow("b9", "B9", "I would use the AI chatbot again for data analysis tasks like this in the future.", b9, setB9)}
                  {renderLikertRow("b10", "B10", "I would recommend the AI chatbot to others for data analysis tasks like this.", b10, setB10)}
                  {renderLikertRow("b11", "B11", "Overall, I am satisfied with the AI chatbot experience.", b11, setB11)}
                </div>
              </div>
            </>
          )}

          {/* Section C: Open Feedback */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-5">
            <div className="bg-gray-50 border-b border-gray-200 rounded-t-xl px-5 py-3">
              <h2 className="text-base font-semibold text-gray-700">Additional Feedback</h2>
              <p className="text-xs text-gray-400">Optional — share any thoughts about your experience</p>
            </div>
            <div className="px-5 py-4 space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">
                  C1. Any additional comments or suggestions?
                </label>
                <textarea
                  value={c1}
                  onChange={(e) => setC1(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none text-sm"
                  placeholder="Share your thoughts..."
                />
              </div>
              {isExperimental && (
                <>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      C2. What did you like about the AI chatbot?
                    </label>
                    <textarea
                      value={c2}
                      onChange={(e) => setC2(e.target.value)}
                      rows={3}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none resize-none text-sm"
                      placeholder="Share what worked well..."
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      C3. What can be improved about the AI chatbot?
                    </label>
                    <textarea
                      value={c3}
                      onChange={(e) => setC3(e.target.value)}
                      rows={3}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none resize-none text-sm"
                      placeholder="Share your suggestions for improvement..."
                    />
                  </div>
                </>
              )}
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            disabled={loading || !isFormComplete()}
            className="w-full"
          >
            {loading ? "Submitting..." : "Submit Survey"}
          </Button>
        </form>
      </div>
    </div>
  );
}
