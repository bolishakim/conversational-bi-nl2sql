"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";
import Button from "./Button";

// Predefined users for the experiment
// IMPORTANT: Each participant account is dedicated to one experiment group
// - user1: ALL Experimental group participants use this account
// - user2: ALL Control group participants use this account
const USERS = [
  {
    email: "admin@adventureworks.com",
    password: "admin123",
    label: "Administrator",
    description: "Full access - for researcher/admin only",
  },
  {
    email: "user1@adventureworks.com",
    password: "experiment123",
    label: "Experimental Group Login",
    description: "For participants assigned to Experimental group (AI Chatbot + Dashboards)",
  },
  {
    email: "user2@adventureworks.com",
    password: "control123",
    label: "Control Group Login",
    description: "For participants assigned to Control group (Dashboards only)",
  },
];

export default function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedUserIndex, setSelectedUserIndex] = useState<number | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedUser = selectedUserIndex !== null ? USERS[selectedUserIndex] : null;

  // Prolific sends real IDs as opaque 24-char hex strings. If the study
  // URL is misconfigured, Prolific can send us the unexpanded template
  // ({{%PROLIFIC_PID%}}) literally. Reject anything that looks templated
  // or obviously not an ID so we never create a pseudo-Prolific participant.
  const isValidProlificId = (v: string | null): v is string =>
    !!v && !/[{}%]/.test(v) && v.length >= 8 && v.length <= 64;

  // Capture Prolific URL parameters and store in sessionStorage
  useEffect(() => {
    const prolificPid = searchParams.get("PROLIFIC_PID");
    const studyId = searchParams.get("STUDY_ID");
    const sessionId = searchParams.get("SESSION_ID");
    const condition = searchParams.get("condition");
    if (isValidProlificId(prolificPid)) {
      sessionStorage.setItem("PROLIFIC_PID", prolificPid);
      if (isValidProlificId(studyId)) sessionStorage.setItem("PROLIFIC_STUDY_ID", studyId);
      if (isValidProlificId(sessionId)) sessionStorage.setItem("PROLIFIC_SESSION_ID", sessionId);
      if (condition === "control" || condition === "experimental") {
        sessionStorage.setItem("PROLIFIC_CONDITION", condition);
      }
    }
  }, [searchParams]);

  // Auto-login for Prolific participants: if the URL identifies them as
  // Prolific AND declares a valid condition, sign them in silently with the
  // shared account that matches the condition's role. They never see the
  // login form.
  const [autoLoginAttempted, setAutoLoginAttempted] = useState(false);
  useEffect(() => {
    if (autoLoginAttempted) return;
    const prolificPid = searchParams.get("PROLIFIC_PID");
    const condition = searchParams.get("condition");
    if (!isValidProlificId(prolificPid) || (condition !== "control" && condition !== "experimental")) {
      return;
    }
    setAutoLoginAttempted(true);
    const user = condition === "experimental" ? USERS[1] : USERS[2];
    setLoading(true);
    (async () => {
      try {
        const response = await api.login({ email: user.email, password: user.password });
        auth.setToken(response.access_token);
        router.push("/onboarding");
      } catch (err: any) {
        setError(err?.message || "Auto-login failed; please sign in manually.");
        setLoading(false);
      }
    })();
  }, [searchParams, autoLoginAttempted, router]);

  // Prefetch pages on mount to speed up navigation
  useEffect(() => {
    router.prefetch("/chat");
    router.prefetch("/onboarding");
    router.prefetch("/dashboards/sales");
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (selectedUserIndex === null) {
      setError("Please select a user");
      return;
    }

    setLoading(true);

    try {
      const user = USERS[selectedUserIndex];
      console.log(`Attempting login...`, { email: user.email });

      const response = await api.login({
        email: user.email,
        password: password
      });

      console.log("Auth successful, token received");

      // Store token
      auth.setToken(response.access_token);

      // Admin goes directly to chat (no onboarding needed)
      if (user.email === "admin@adventureworks.com") {
        router.push("/chat");
        return;
      }

      // Both Control and Experimental groups go through onboarding
      // The onboarding page will redirect to appropriate destination after completion
      router.push("/onboarding");
    } catch (err: any) {
      console.error("Auth error:", err);
      setError(err.message || "Invalid password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white px-6">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-white rounded-lg shadow-lg border border-border p-8">
          {/* Header */}
          <h1 className="text-3xl font-bold text-center mb-2">
            Welcome
          </h1>
          <p className="text-center text-gray-600 mb-8">
            Select your account to sign in
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* User Selection Dropdown */}
            <div>
              <label
                htmlFor="user"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Select User
              </label>
              <select
                id="user"
                value={selectedUserIndex ?? ""}
                onChange={(e) => {
                  const index = e.target.value === "" ? null : parseInt(e.target.value);
                  setSelectedUserIndex(index);
                  setPassword("");
                  setError("");
                }}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none bg-white"
              >
                <option value="">-- Select a user --</option>
                {USERS.map((user, index) => (
                  <option key={user.email} value={index}>
                    {user.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="Enter password"
                disabled={selectedUserIndex === null}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              disabled={loading || selectedUserIndex === null}
              className="w-full"
            >
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
