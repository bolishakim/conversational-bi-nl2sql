"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  TrendingUp,
  Package,
  Users,
  LayoutDashboard,
  Bot,
  History,
  Lock,
  LogOut,
  ClipboardList,
  Settings
} from "lucide-react";
import Logo from "./Logo";
import { api } from "@/lib/api";
import { auth } from "@/lib/auth";
import type { User } from "@/types/auth";
import type { ExperimentParticipant } from "@/types/experiment";

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
  active: boolean;
  comingSoon?: boolean;
}

interface NavSection {
  title: string;
  icon: React.ReactNode;
  items: NavItem[];
  requiresChatbotAccess?: boolean;
}

interface SidebarProps {
  user: User | null;
}

// Helper function to create abbreviated name (e.g., "Bolis Hakim" -> "B. Hakim")
function getAbbreviatedName(fullName: string | undefined): string {
  if (!fullName) return "Participant";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return fullName;
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  return `${firstName.charAt(0).toUpperCase()}. ${lastName}`;
}

// Helper function to get initials for avatar (e.g., "Bolis Hakim" -> "BH")
function getInitials(fullName: string | undefined): string {
  if (!fullName) return "P";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

export default function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const [participant, setParticipant] = useState<ExperimentParticipant | null>(null);

  // Fetch participant info on mount
  useEffect(() => {
    const fetchParticipant = async () => {
      try {
        const response = await api.getOnboardingStatus();
        if (response.participant) {
          setParticipant(response.participant as ExperimentParticipant);
        }
      } catch (error) {
        console.error("Failed to fetch participant info:", error);
      }
    };

    if (user && user.role !== 'admin') {
      fetchParticipant();
    }
  }, [user]);

  const handleLogout = () => {
    auth.removeToken();
    window.location.href = "/login";
  };

  // Check if user has chatbot access (admin or experimental group)
  const canAccessChatbot = user?.can_access_chatbot ?? false;

  // Only show Study Tasks for non-admin users (participants)
  const isParticipant = user?.role !== 'admin';
  const isAdmin = user?.role === 'admin';

  const navSections: NavSection[] = [
    // Study Tasks section (only for participants) - placed first
    ...(isParticipant ? [{
      title: "Study Tasks",
      icon: <ClipboardList className="w-4 h-4" />,
      items: [
        {
          name: "My Tasks",
          href: "/tasks",
          icon: <ClipboardList className="w-5 h-5" />,
          active: true,
        },
      ],
    }] : []),
    {
      title: "Dashboards",
      icon: <LayoutDashboard className="w-4 h-4" />,
      items: [
        {
          name: "Sales & Revenue",
          href: "/dashboards/sales",
          icon: <TrendingUp className="w-5 h-5" />,
          active: true,
        },
        {
          name: "Production & Inventory",
          href: "/dashboards/production",
          icon: <Package className="w-5 h-5" />,
          active: true,
        },
        {
          name: "Workforce & Operations",
          href: "/dashboards/operations",
          icon: <Users className="w-5 h-5" />,
          active: true,
        },
      ],
    },
    {
      title: "AI Assistant",
      icon: <Bot className="w-4 h-4" />,
      requiresChatbotAccess: true,
      items: [
        {
          name: "Query Assistant",
          href: "/chat",
          icon: <MessageSquare className="w-5 h-5" />,
          active: true,
        },
        {
          name: "Query History",
          href: "/chat/history",
          icon: <History className="w-5 h-5" />,
          active: true,
        },
      ],
    },
    // Admin section (only for admins)
    ...(isAdmin ? [{
      title: "Admin",
      icon: <Settings className="w-4 h-4" />,
      items: [
        {
          name: "Participant Tracking",
          href: "/admin",
          icon: <Users className="w-5 h-5" />,
          active: true,
        },
      ],
    }] : []),
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Logo/Brand */}
      <div className="px-4 py-5 border-b border-gray-200">
        <Logo size="md" showSubtitle={true} />
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {navSections.map((section) => {
          // Check if section requires chatbot access
          const sectionLocked = section.requiresChatbotAccess && !canAccessChatbot;

          return (
            <div key={section.title}>
              {/* Section Header */}
              <div className="flex items-center gap-2 px-3 mb-2">
                <span className={sectionLocked ? "text-gray-300" : "text-gray-400"}>
                  {section.icon}
                </span>
                <span className={`text-xs font-semibold uppercase tracking-wider ${
                  sectionLocked ? "text-gray-300" : "text-gray-400"
                }`}>
                  {section.title}
                </span>
                {sectionLocked && (
                  <Lock className="w-3 h-3 text-gray-300 ml-auto" />
                )}
              </div>

              {/* Section Items */}
              <div className="space-y-1">
                {section.items.map((item) => {
                  const isActive = pathname === item.href;
                  const isClickable = item.active && !sectionLocked;

                  return (
                    <div key={item.name} className="relative">
                      {isClickable ? (
                        <Link
                          href={item.href}
                          className={`
                            flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                            ${
                              isActive
                                ? "bg-blue-50 text-blue-600"
                                : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                            }
                          `}
                        >
                          {item.icon}
                          <span>{item.name}</span>
                        </Link>
                      ) : (
                        <div
                          className={`
                            flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium cursor-not-allowed
                            ${sectionLocked ? "text-gray-300" : "text-gray-400 opacity-60"}
                          `}
                          title={sectionLocked ? "Not available for your account" : undefined}
                        >
                          {item.icon}
                          <span>{item.name}</span>
                          {item.comingSoon && (
                            <span className="ml-auto text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                              Soon
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* User Info Section */}
      {user && (
        <div className="px-3 py-3 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center gap-3">
            {/* Avatar with initials */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
              user.role === 'admin'
                ? 'bg-purple-100 text-purple-700'
                : participant?.condition_assigned === 'experimental'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-orange-100 text-orange-700'
            }`}>
              {user.role === 'admin'
                ? 'A'
                : participant?.participant_code?.substring(0, 2) || 'P'}
            </div>

            {/* User details */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user.role === 'admin'
                  ? 'Administrator'
                  : `Participant ${participant?.participant_code || ''}`}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {user.role === 'admin'
                  ? 'Full Access'
                  : participant?.participant_code || 'Loading...'}
              </p>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          {/* Condition badge for participants */}
          {user.role !== 'admin' && participant && (
            <div className={`mt-2 text-xs px-2 py-1 rounded-full text-center ${
              participant.condition_assigned === 'experimental'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-orange-100 text-orange-700'
            }`}>
              {participant.condition_assigned === 'experimental'
                ? 'Experimental Group'
                : 'Control Group'}
            </div>
          )}

          {user.role === 'admin' && (
            <div className="mt-2 text-xs px-2 py-1 rounded-full text-center bg-purple-100 text-purple-700">
              Admin Access
            </div>
          )}
        </div>
      )}

    </aside>
  );
}
