"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";
import Button from "@/components/Button";
import type {
  RegisterParticipantRequest,
  ActiveExperimentResponse,
  OccupationOption,
  VisualAnalyticsFrequency,
  BusinessBackground,
  LLMChatbotExperience,
  BIToolsExperience,
} from "@/types";

type OnboardingStep = "choice" | "welcome" | "consent" | "pre-survey" | "returning-participant" | "success";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>("choice");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeExperiment, setActiveExperiment] = useState<ActiveExperimentResponse | null>(null);
  const [successData, setSuccessData] = useState<{ participantCode: string; condition: string } | null>(null);

  // Welcome step state
  const [hasReadExplanation, setHasReadExplanation] = useState(false);

  // User role for showing correct tutorial video
  const [userRole, setUserRole] = useState<string | null>(null);

  // Consent state
  const [consentChecks, setConsentChecks] = useState({
    informed_consent: false,
    ageConfirm: false,
    data_protection: false,
  });

  // Pre-survey form state
  const [surveyData, setSurveyData] = useState({
    age: "" as number | "",
    occupation_statuses: [] as OccupationOption[],
    field_of_work: "",
    field_of_work_other: "",
    field_of_study: "",
    field_of_study_other: "",
    visual_analytics_frequency: "" as VisualAnalyticsFrequency | "",
    business_background: "" as BusinessBackground | "",
    llm_chatbot_experience: "" as LLMChatbotExperience | "",
    bi_tools_experience: "" as BIToolsExperience | "",
  });

  // Returning participant state
  const [participantCode, setParticipantCode] = useState("");

  useEffect(() => {
    // Check if user is authenticated
    if (!auth.getToken()) {
      router.push("/login");
      return;
    }

    // Get active experiment
    checkOnboardingStatus();
  }, []);

  // Video ID based on user role
  const tutorialVideoId = userRole === "participant_experimental" ? "ucVfgCaHguo" : "3Il1244UOVM";

  const checkOnboardingStatus = async () => {
    try {
      const [experimentResponse, userData] = await Promise.all([
        api.getActiveExperiment(),
        api.me(),
      ]);
      setActiveExperiment(experimentResponse);
      setUserRole(userData.role);

      if (!experimentResponse.has_active_experiment) {
        setError("No active experiment found. Please contact the administrator.");
      }
    } catch (err: any) {
      console.error("Error checking onboarding status:", err);
      setError(err.message || "Failed to check onboarding status");
    }
  };

  const handleNewParticipantStart = () => {
    setStep("welcome");
  };

  const handleContinueToConsent = () => {
    setStep("consent");
  };

  const handleConsentAgree = () => {
    setStep("pre-survey");
  };

  const handleConsentDecline = () => {
    // Redirect to login or show message
    router.push("/login");
  };

  const allConsentsGiven = () => {
    return consentChecks.informed_consent && consentChecks.ageConfirm && consentChecks.data_protection;
  };

  const isStudent = surveyData.occupation_statuses.includes("student");
  const hasNonStudent = surveyData.occupation_statuses.some(o => o !== "student");

  const isSurveyComplete = () => {
    if (surveyData.age === "" || surveyData.occupation_statuses.length === 0) return false;

    // Conditional field validation
    if (hasNonStudent) {
      const fieldOfWork = surveyData.field_of_work === "other" ? surveyData.field_of_work_other : surveyData.field_of_work;
      if (!fieldOfWork) return false;
    }
    if (isStudent) {
      const fieldOfStudy = surveyData.field_of_study === "other" ? surveyData.field_of_study_other : surveyData.field_of_study;
      if (!fieldOfStudy) return false;
    }

    return (
      surveyData.visual_analytics_frequency !== "" &&
      surveyData.business_background !== "" &&
      surveyData.llm_chatbot_experience !== "" &&
      surveyData.bi_tools_experience !== ""
    );
  };

  const handleSurveySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (!activeExperiment?.experiment_id) {
        throw new Error("No active experiment found");
      }

      const fieldOfWork = surveyData.field_of_work === "other" ? surveyData.field_of_work_other : surveyData.field_of_work;
      const fieldOfStudy = surveyData.field_of_study === "other" ? surveyData.field_of_study_other : surveyData.field_of_study;

      // Attach Prolific identifiers if the participant arrived via a
      // Prolific URL. AuthForm stashes them in sessionStorage at login; we
      // persist them to the DB here so the participant is tagged as
      // recruitment_source='prolific'. University-cohort participants
      // have no such keys so the fields stay undefined.
      const getSS = (k: string) =>
        typeof window !== "undefined" ? sessionStorage.getItem(k) ?? undefined : undefined;
      const prolificPid = getSS("PROLIFIC_PID");
      const prolificStudyId = getSS("PROLIFIC_STUDY_ID");
      const prolificSessionId = getSS("PROLIFIC_SESSION_ID");
      const prolificCondition = getSS("PROLIFIC_CONDITION");

      const registrationData: RegisterParticipantRequest = {
        experiment_id: activeExperiment.experiment_id,
        age: surveyData.age as number,
        occupation_statuses: surveyData.occupation_statuses,
        field_of_work: hasNonStudent ? fieldOfWork : undefined,
        field_of_study: isStudent ? fieldOfStudy : undefined,
        visual_analytics_frequency: surveyData.visual_analytics_frequency as VisualAnalyticsFrequency,
        business_background: surveyData.business_background as BusinessBackground,
        llm_chatbot_experience: surveyData.llm_chatbot_experience as LLMChatbotExperience,
        bi_tools_experience: surveyData.bi_tools_experience as BIToolsExperience,
        consent_given: true,
        prolific_pid: prolificPid,
        prolific_study_id: prolificStudyId,
        prolific_session_id: prolificSessionId,
        prolific_condition:
          prolificCondition === "control" || prolificCondition === "experimental"
            ? prolificCondition
            : undefined,
      };

      const response = await api.registerParticipant(registrationData);

      // Persist the participant_id returned by the server. Every later
      // request that needs to identify "this participant" (survey submit,
      // /participants/me, etc.) reads this instead of relying on
      // user-account-based lookup, which is ambiguous under the shared
      // account model when multiple Prolific participants register at once.
      if (typeof window !== "undefined" && response.participant_id) {
        sessionStorage.setItem("PARTICIPANT_ID", response.participant_id);
      }

      setSuccessData({
        participantCode: response.participant_code,
        condition: response.condition_assigned,
      });
      setStep("success");
    } catch (err: any) {
      console.error("Registration error:", err);
      setError(err.message || "Failed to register. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReturningParticipantSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.lookupParticipant({
        participant_code: participantCode.toUpperCase(),
      });

      if (response.found && response.participant) {
        // Stash participant_id for unambiguous /participants/me lookups going
        // forward (see shared-account comment in register flow).
        if (typeof window !== "undefined" && response.participant.id) {
          sessionStorage.setItem("PARTICIPANT_ID", response.participant.id);
        }
        router.push("/tasks");
      } else {
        setError(response.message || "Participant not found. Please check your ID or register as a new participant.");
      }
    } catch (err: any) {
      console.error("Lookup error:", err);
      setError(err.message || "Failed to find participant. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleContinueToExperiment = () => {
    router.push("/tasks");
  };

  // Choice screen
  if (step === "choice") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6">
        <div className="w-full max-w-lg">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8">
            <h1 className="text-2xl font-bold text-center mb-2">Welcome to the Study</h1>
            <p className="text-center text-gray-600 mb-8">
              Please select an option to continue.
            </p>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm mb-6">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <button
                onClick={handleNewParticipantStart}
                disabled={!activeExperiment?.has_active_experiment}
                className="w-full p-6 border-2 border-blue-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <h3 className="text-lg font-semibold text-blue-700">I am a New Participant</h3>
                <p className="text-gray-600 text-sm mt-1">
                  First time participating? Start here to register.
                </p>
              </button>

              <button
                onClick={() => setStep("returning-participant")}
                disabled={!activeExperiment?.has_active_experiment}
                className="w-full p-6 border-2 border-green-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <h3 className="text-lg font-semibold text-green-700">I am a Returning Participant</h3>
                <p className="text-gray-600 text-sm mt-1">
                  Already have a Participant ID? Continue your session here.
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Welcome & Explanation screen
  if (step === "welcome") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6 py-8">
        <div className="w-full max-w-5xl">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8">
            <button
              onClick={() => setStep("choice")}
              className="text-blue-600 hover:text-blue-800 mb-4 flex items-center text-sm"
            >
              &larr; Back
            </button>

            <h1 className="text-2xl font-bold text-center mb-2">Welcome to the Business Intelligence Study</h1>
            <p className="text-center text-gray-600 mb-6">
              Thank you for participating in this research study as part of a Master&apos;s thesis at TU Graz.
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold text-blue-800 mb-4">What to Expect</h2>
              <ul className="space-y-2 text-gray-700">
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2">&#8226;</span>
                  <span><strong>Duration:</strong> Approximately 30-45 minutes</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2">&#8226;</span>
                  <span><strong>Tasks:</strong> 5 tasks involving business data analysis</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2">&#8226;</span>
                  <span><strong>Questionnaires:</strong> Brief surveys before and after tasks</span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2">&#8226;</span>
                  <span><strong>Recording:</strong> Your responses will be recorded for research purposes</span>
                </li>
              </ul>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Study Process</h2>
              <ol className="space-y-2 text-gray-700 list-decimal list-inside">
                <li>Read and consent to participate</li>
                <li>Answer 7 quick background questions</li>
                <li>Complete 5 data analysis tasks</li>
                <li>Answer a brief post-study questionnaire</li>
              </ol>
            </div>

            {/* Tutorial Video */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4 text-center">Tutorial Video</h2>
              <p className="text-sm text-gray-600 text-center mb-4">Please watch this short tutorial before proceeding.</p>
              <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                <iframe
                  src={`https://www.youtube.com/embed/${tutorialVideoId}?rel=0&modestbranding=1&vq=hd1080`}
                  className="absolute top-0 left-0 w-full h-full rounded-lg"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>

            <label className="flex items-center mb-6 cursor-pointer">
              <input
                type="checkbox"
                checked={hasReadExplanation}
                onChange={(e) => setHasReadExplanation(e.target.checked)}
                className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <span className="ml-3 text-gray-700">I have read and understood the study explanation</span>
            </label>

            <Button
              onClick={handleContinueToConsent}
              variant="primary"
              disabled={!hasReadExplanation}
              className="w-full"
            >
              Continue to Informed Consent
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Consent screen
  if (step === "consent") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6 py-8">
        <div className="w-full max-w-2xl">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8">
            <button
              onClick={() => setStep("welcome")}
              className="text-blue-600 hover:text-blue-800 mb-4 flex items-center text-sm"
            >
              &larr; Back
            </button>

            <h1 className="text-2xl font-bold text-center mb-2">Informed Consent</h1>
            <p className="text-center text-gray-600 mb-6">
              Please read carefully before proceeding
            </p>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6 max-h-64 overflow-y-auto">
              <h3 className="font-semibold text-gray-800 mb-2">Research Study: Conversational Business Intelligence</h3>
              <p className="text-sm text-gray-600 mb-4">
                <strong>Researcher:</strong> Bolis Hakim, TU Graz (Master&apos;s Thesis)<br />
                <strong>Supervisor:</strong> Assoc.-Prof. Dr. Viktoria Pammer-Schindler
              </p>

              <h4 className="font-semibold text-gray-800 mb-2">Purpose of the Study</h4>
              <p className="text-sm text-gray-600 mb-4">
                This research investigates how AI-augmented tools compare to traditional
                business intelligence dashboards for data analysis tasks.
              </p>

              <h4 className="font-semibold text-gray-800 mb-2">What We Collect</h4>
              <ul className="text-sm text-gray-600 mb-4 list-disc list-inside">
                <li>Your answers to tasks</li>
                <li>Time taken to complete tasks</li>
                <li>Your interactions with the system</li>
                <li>Your responses to questionnaires</li>
                <li>Anonymous demographic information</li>
              </ul>

              <h4 className="font-semibold text-gray-800 mb-2">Privacy & Data Protection</h4>
              <ul className="text-sm text-gray-600 mb-4 list-disc list-inside">
                <li>Your data will be anonymized using a Participant ID (not your name)</li>
                <li>No personally identifiable information (name, email, phone, date of birth) is collected</li>
                <li>Data will be used only for this research and academic publications</li>
                <li>Data will be stored securely and deleted after the research is complete</li>
                <li>You can withdraw at any time without penalty</li>
              </ul>

              <h4 className="font-semibold text-gray-800 mb-2">Your Rights</h4>
              <ul className="text-sm text-gray-600 mb-4 list-disc list-inside">
                <li>Participation is voluntary</li>
                <li>You may withdraw at any time</li>
                <li>You may ask questions before, during, or after participation</li>
                <li>You will receive a summary of findings upon request</li>
              </ul>

              <h4 className="font-semibold text-gray-800 mb-2">Withdrawal of Consent</h4>
              <p className="text-sm text-gray-600 mb-4">
                You can withdraw your consent at any time by emailing{" "}
                <a href="mailto:bolis.hakim@student.tugraz.at" className="text-blue-600 hover:underline">bolis.hakim@student.tugraz.at</a>.
                Any processing carried out before withdrawal remains valid.
              </p>

              <h4 className="font-semibold text-gray-800 mb-2">Contact & Data Protection</h4>
              <p className="text-sm text-gray-600 mb-2">
                For questions, complaints, or to request deletion of your data, contact:<br />
                <a href="mailto:bolis.hakim@student.tugraz.at" className="text-blue-600 hover:underline">bolis.hakim@student.tugraz.at</a>
              </p>
              <p className="text-sm text-gray-600">
                For data protection information, see the{" "}
                <a href="https://www.cis.tugraz.at/international/information_en.shtml" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  TU Graz Data Protection Information
                </a>.
              </p>
            </div>

            <div className="space-y-4 mb-6">
              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentChecks.informed_consent}
                  onChange={(e) => setConsentChecks({ ...consentChecks, informed_consent: e.target.checked })}
                  className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-3 text-gray-700 text-sm">
                  I have read and understood the above information, I voluntarily agree to participate in this study, and I understand my anonymized data will be used for research purposes
                </span>
              </label>

              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentChecks.ageConfirm}
                  onChange={(e) => setConsentChecks({ ...consentChecks, ageConfirm: e.target.checked })}
                  className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-3 text-gray-700 text-sm">I am at least 18 years old</span>
              </label>

              <label className="flex items-start cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentChecks.data_protection}
                  onChange={(e) => setConsentChecks({ ...consentChecks, data_protection: e.target.checked })}
                  className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="ml-3 text-gray-700 text-sm">
                  I have read and understood the{" "}
                  <a href="https://www.cis.tugraz.at/international/information_en.shtml" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">data protection information</a>
                </span>
              </label>
            </div>

            <div className="flex gap-4">
              <Button
                onClick={handleConsentDecline}
                variant="secondary"
                className="flex-1"
              >
                I Do Not Consent
              </Button>
              <Button
                onClick={handleConsentAgree}
                variant="primary"
                disabled={!allConsentsGiven()}
                className="flex-1"
              >
                I Consent - Continue
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Pre-survey screen
  if (step === "pre-survey") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6 py-8">
        <div className="w-full max-w-2xl">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8">
            <button
              onClick={() => setStep("consent")}
              className="text-blue-600 hover:text-blue-800 mb-4 flex items-center text-sm"
            >
              &larr; Back
            </button>

            <h1 className="text-2xl font-bold text-center mb-2">About You</h1>
            <p className="text-center text-gray-600 mb-6">
              Please answer these 7 questions. All information is anonymous.
            </p>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSurveySubmit} className="space-y-6">
              {/* Q1: Age (exact) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  1. What is your age (in years)? <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  min={18}
                  max={99}
                  value={surveyData.age}
                  onChange={(e) => setSurveyData({ ...surveyData, age: e.target.value ? parseInt(e.target.value) : "" })}
                  placeholder="e.g., 25"
                  className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                />
              </div>

              {/* Q2: Occupation + conditional Field of Study/Work */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  2. Which of the following applies to you? (Select all that apply) <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {[
                    { value: "student" as OccupationOption, label: "Student" },
                    { value: "employee" as OccupationOption, label: "Employee" },
                    { value: "self_employed" as OccupationOption, label: "Self-employed" },
                    { value: "other" as OccupationOption, label: "Other" },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={surveyData.occupation_statuses.includes(option.value)}
                        onChange={(e) => {
                          const updated = e.target.checked
                            ? [...surveyData.occupation_statuses, option.value]
                            : surveyData.occupation_statuses.filter(o => o !== option.value);
                          setSurveyData({ ...surveyData, occupation_statuses: updated });
                        }}
                        className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-gray-700">{option.label}</span>
                    </label>
                  ))}
                </div>

                {/* Conditional: Field of Study (when student selected) */}
                {isStudent && (
                  <div className="mt-4 ml-4 pl-4 border-l-2 border-blue-200">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Field of Study <span className="text-red-500">*</span>
                    </label>
                    <div className="space-y-2">
                      {[
                        { value: "business", label: "Business/Management" },
                        { value: "computer_science", label: "Computer Science/IT" },
                        { value: "engineering", label: "Engineering" },
                        { value: "natural_sciences", label: "Natural Sciences" },
                        { value: "social_sciences", label: "Social Sciences/Humanities" },
                        { value: "other", label: "Other" },
                      ].map((option) => (
                        <label key={option.value} className="flex items-center cursor-pointer">
                          <input
                            type="radio"
                            name="field_of_study"
                            value={option.value}
                            checked={surveyData.field_of_study === option.value}
                            onChange={(e) => setSurveyData({ ...surveyData, field_of_study: e.target.value })}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                          />
                          <span className="ml-3 text-gray-700">{option.label}</span>
                        </label>
                      ))}
                    </div>
                    {surveyData.field_of_study === "other" && (
                      <input
                        type="text"
                        value={surveyData.field_of_study_other}
                        onChange={(e) => setSurveyData({ ...surveyData, field_of_study_other: e.target.value })}
                        placeholder="Please specify..."
                        className="mt-2 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    )}
                  </div>
                )}

                {/* Conditional: Field of Work (when employee/self_employed/other selected) */}
                {hasNonStudent && (
                  <div className="mt-4 ml-4 pl-4 border-l-2 border-blue-200">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Field of Work <span className="text-red-500">*</span>
                    </label>
                    <div className="space-y-2">
                      {[
                        { value: "business", label: "Business/Management" },
                        { value: "computer_science", label: "Computer Science/IT" },
                        { value: "engineering", label: "Engineering" },
                        { value: "natural_sciences", label: "Natural Sciences" },
                        { value: "social_sciences", label: "Social Sciences/Humanities" },
                        { value: "other", label: "Other" },
                      ].map((option) => (
                        <label key={option.value} className="flex items-center cursor-pointer">
                          <input
                            type="radio"
                            name="field_of_work"
                            value={option.value}
                            checked={surveyData.field_of_work === option.value}
                            onChange={(e) => setSurveyData({ ...surveyData, field_of_work: e.target.value })}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                          />
                          <span className="ml-3 text-gray-700">{option.label}</span>
                        </label>
                      ))}
                    </div>
                    {surveyData.field_of_work === "other" && (
                      <input
                        type="text"
                        value={surveyData.field_of_work_other}
                        onChange={(e) => setSurveyData({ ...surveyData, field_of_work_other: e.target.value })}
                        placeholder="Please specify..."
                        className="mt-2 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    )}
                  </div>
                )}
              </div>

              {/* Q3: Visual Analytics Frequency (was Q4) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  3. How often do you work with visual data analytics (charts, graphs, dashboards)? <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {[
                    { value: "never", label: "Never" },
                    { value: "rarely", label: "Rarely (few times per year)" },
                    { value: "occasionally", label: "Occasionally (monthly)" },
                    { value: "regularly", label: "Regularly (weekly)" },
                    { value: "daily", label: "Daily" },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="visual_analytics_frequency"
                        value={option.value}
                        checked={surveyData.visual_analytics_frequency === option.value}
                        onChange={(e) => setSurveyData({ ...surveyData, visual_analytics_frequency: e.target.value as VisualAnalyticsFrequency })}
                        className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-gray-700">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Q4: Business Background */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  4. Do you have a background in business (education or work experience)? <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {[
                    { value: "education", label: "Yes, formal education (degree/courses)" },
                    { value: "experience", label: "Yes, work experience" },
                    { value: "both", label: "Yes, both education and experience" },
                    { value: "none", label: "No background in business" },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="business_background"
                        value={option.value}
                        checked={surveyData.business_background === option.value}
                        onChange={(e) => setSurveyData({ ...surveyData, business_background: e.target.value as BusinessBackground })}
                        className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-gray-700">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Q5: LLM Chatbot Experience */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  5. Have you used LLM-powered chatbots before (e.g., ChatGPT, Claude, Gemini)? <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {[
                    { value: "never", label: "No, never" },
                    { value: "once_twice", label: "Yes, tried once or twice" },
                    { value: "occasionally", label: "Yes, use occasionally (few times per month)" },
                    { value: "regularly", label: "Yes, use regularly (weekly or more)" },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="llm_chatbot_experience"
                        value={option.value}
                        checked={surveyData.llm_chatbot_experience === option.value}
                        onChange={(e) => setSurveyData({ ...surveyData, llm_chatbot_experience: e.target.value as LLMChatbotExperience })}
                        className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-gray-700">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Q6: BI Tools Experience */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  6. Do you have prior experience with BI tools (e.g., Power BI, Tableau, Looker)? <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {[
                    { value: "none", label: "No experience" },
                    { value: "minimal", label: "Minimal (seen demos, not used personally)" },
                    { value: "basic", label: "Basic (used occasionally)" },
                    { value: "intermediate", label: "Intermediate (regular user)" },
                    { value: "advanced", label: "Advanced (power user, create dashboards)" },
                  ].map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer">
                      <input
                        type="radio"
                        name="bi_tools_experience"
                        value={option.value}
                        checked={surveyData.bi_tools_experience === option.value}
                        onChange={(e) => setSurveyData({ ...surveyData, bi_tools_experience: e.target.value as BIToolsExperience })}
                        className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <span className="ml-3 text-gray-700">{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={loading || !isSurveyComplete()}
                className="w-full mt-6"
              >
                {loading ? "Registering..." : "Complete Registration"}
              </Button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Returning participant screen
  if (step === "returning-participant") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6">
        <div className="w-full max-w-lg">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8">
            <button
              onClick={() => setStep("choice")}
              className="text-blue-600 hover:text-blue-800 mb-4 flex items-center text-sm"
            >
              &larr; Back
            </button>

            <h1 className="text-2xl font-bold text-center mb-2">Welcome Back</h1>
            <p className="text-center text-gray-600 mb-6">
              Enter your Participant ID to continue your session
            </p>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleReturningParticipantSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Participant ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={participantCode}
                  onChange={(e) => setParticipantCode(e.target.value.toUpperCase())}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  placeholder="e.g., P001"
                />
                <p className="text-xs text-gray-500 mt-1">
                  This is the ID you received when you first registered
                </p>
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={loading || !participantCode}
                className="w-full mt-6"
              >
                {loading ? "Looking up..." : "Continue Session"}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-500">
                Don&apos;t have a participant ID?{" "}
                <button
                  onClick={handleNewParticipantStart}
                  className="text-blue-600 hover:underline"
                >
                  Register as new participant
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Success screen
  if (step === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6">
        <div className="w-full max-w-lg">
          <div className="bg-white rounded-lg shadow-lg border border-border p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h1 className="text-2xl font-bold mb-2">Registration Successful!</h1>
            <p className="text-gray-600 mb-6">
              You have been successfully registered for the study.
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-600 mb-2">Your Participant ID:</p>
              <p className="text-3xl font-bold text-blue-700">{successData?.participantCode}</p>
              <p className="text-xs text-gray-500 mt-2">
                Please save this ID - you can use it to continue your session if needed.
              </p>
            </div>

            <div className={`border rounded-lg p-4 mb-6 ${
              successData?.condition === 'experimental'
                ? 'bg-purple-50 border-purple-200'
                : 'bg-orange-50 border-orange-200'
            }`}>
              <p className="text-sm text-gray-600 mb-1">You have been assigned to:</p>
              <p className={`text-lg font-semibold ${
                successData?.condition === 'experimental'
                  ? 'text-purple-700'
                  : 'text-orange-700'
              }`}>
                {successData?.condition === 'experimental' ? 'Experimental Group' : 'Control Group'}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {successData?.condition === 'experimental'
                  ? 'You will have access to Dashboards + AI Query Assistant'
                  : 'You will have access to Dashboards'}
              </p>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 text-left">
              <h3 className="font-semibold text-gray-800 mb-2">Ready to Begin!</h3>
              <p className="text-sm text-gray-600 mb-2">
                You will now complete 5 analysis tasks using the Adventure Works dataset.
              </p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>&#10003; Task 1 is a TUTORIAL - take your time to explore</li>
                <li>&#10003; Answer to the best of your ability</li>
                <li>&#10003; You can submit &quot;I don&apos;t know&quot; if needed</li>
              </ul>
            </div>

            <Button
              onClick={handleContinueToExperiment}
              variant="primary"
              className="w-full"
            >
              Start Tasks
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
