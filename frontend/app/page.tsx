"use client";

import Link from "next/link";
import Logo from "@/components/Logo";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-blue-50 to-white">
      <div className="max-w-2xl mx-auto px-6 text-center">
        {/* Header */}
        <div className="flex justify-center mb-6">
          <Logo size="lg" showSubtitle={false} />
        </div>
        <p className="text-xl text-gray-600 mb-12">
          Transform natural language questions into SQL queries with AI-powered analysis and visualization
        </p>

        {/* CTA Button */}
        <div className="flex justify-center">
          <Link
            href="/login"
            className="px-8 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            Login
          </Link>
        </div>

        {/* Features */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-lg shadow-sm border border-border">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="font-semibold text-lg mb-2">AI-Powered</h3>
            <p className="text-sm text-gray-600">
              Claude 3.5 Sonnet generates accurate SQL from natural language
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-sm border border-border">
            <div className="text-3xl mb-3">📊</div>
            <h3 className="font-semibold text-lg mb-2">Smart Insights</h3>
            <p className="text-sm text-gray-600">
              Automatic analysis and visualizations for your data
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-sm border border-border">
            <div className="text-3xl mb-3">⚡</div>
            <h3 className="font-semibold text-lg mb-2">Fast Results</h3>
            <p className="text-sm text-gray-600">
              Get answers in seconds, no SQL knowledge required
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
