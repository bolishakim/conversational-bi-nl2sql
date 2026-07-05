"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { User } from "@/types/auth";
import Sidebar from "./Sidebar";
import Header from "./Header";
import Footer from "./Footer";

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  showFooter?: boolean;
}

export default function AuthenticatedLayout({
  children,
  title,
  subtitle,
  showFooter = false,
}: AuthenticatedLayoutProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check authentication and fetch user data
    const checkAuth = async () => {
      if (!auth.isAuthenticated()) {
        router.push("/login");
        return;
      }

      try {
        const userData = await api.me();
        setUser(userData);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch user data:", error);
        auth.removeToken();
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="text-gray-600 mt-3">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <Sidebar user={user} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header title={title} subtitle={subtitle} />

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">{children}</main>

        {/* Footer (optional) */}
        {showFooter && <Footer />}
      </div>
    </div>
  );
}
