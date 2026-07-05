"use client";

import { Mail, BookOpen, GitBranch } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-gray-200 px-6 py-4">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Section - Copyright */}
        <div className="text-sm text-gray-600">
          <p>
            <span className="font-semibold">Talk2Data</span> © {currentYear}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Master's Thesis Project - AdventureWorks Database 2022-2025
          </p>
        </div>

        {/* Right Section - Links */}
        <div className="flex items-center gap-6">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <GitBranch className="w-4 h-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <a
            href="mailto:support@example.com"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <Mail className="w-4 h-4" />
            <span className="hidden sm:inline">Contact</span>
          </a>
          <a
            href="#"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <BookOpen className="w-4 h-4" />
            <span className="hidden sm:inline">Documentation</span>
          </a>
        </div>
      </div>
    </footer>
  );
}
