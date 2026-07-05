"use client";

import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";
import { useTaskSession } from "@/contexts/TaskSessionContext";
import { LogOut, User } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  const router = useRouter();
  const { resetSession } = useTaskSession();

  const handleLogout = () => {
    // Reset task session state before logging out
    resetSession();
    auth.removeToken();
    router.push("/");
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
      {/* Title Section */}
      <div>
        <h1 className="text-xl font-bold text-gray-800">{title}</h1>
        {subtitle && (
          <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
        )}
      </div>

      {/* User Actions */}
      <div className="flex items-center gap-4">
        {/* User Info */}
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <User className="w-4 h-4" />
          <span className="hidden sm:inline">Account</span>
        </div>

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}
