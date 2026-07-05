"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ParticipantSummary } from "@/types/admin";
import { ArrowUpDown } from "lucide-react";

interface ParticipantListProps {
  participants: ParticipantSummary[];
}

type SortField = keyof ParticipantSummary | "none";
type SortDirection = "asc" | "desc";

export default function ParticipantList({ participants }: ParticipantListProps) {
  const router = useRouter();
  const [sortField, setSortField] = useState<SortField>("participant_code");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [filterCondition, setFilterCondition] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSource, setFilterSource] = useState<string>("all");

  // Filter participants
  let filteredParticipants = [...participants];

  if (filterCondition !== "all") {
    filteredParticipants = filteredParticipants.filter(
      (p) => p.condition_assigned === filterCondition
    );
  }

  if (filterStatus !== "all") {
    filteredParticipants = filteredParticipants.filter(
      (p) => p.status === filterStatus
    );
  }

  if (filterSource !== "all") {
    filteredParticipants = filteredParticipants.filter(
      (p) => (p.recruitment_source ?? "university") === filterSource
    );
  }

  // Sort participants
  if (sortField !== "none") {
    filteredParticipants.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (aVal === null) return 1;
      if (bVal === null) return -1;

      let comparison = 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        comparison = aVal.localeCompare(bVal);
      } else if (typeof aVal === "number" && typeof bVal === "number") {
        comparison = aVal - bVal;
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const formatDuration = (minutes: number | null) => {
    if (minutes === null) return "N/A";
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const formatLastActivity = (timestamp: string | null) => {
    if (!timestamp) return "Never";
    const date = new Date(timestamp);
    const now = new Date();
    const diffMinutes = (now.getTime() - date.getTime()) / (1000 * 60);

    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${Math.round(diffMinutes)}m ago`;
    if (diffMinutes < 1440) return `${Math.round(diffMinutes / 60)}h ago`;
    return `${Math.round(diffMinutes / 1440)}d ago`;
  };

  const getConditionBadge = (condition: string) => {
    const isControl = condition === "control";
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          isControl
            ? "bg-blue-100 text-blue-800"
            : "bg-purple-100 text-purple-800"
        }`}
      >
        {isControl ? "Control" : "Experimental"}
      </span>
    );
  };

  const getSourceBadge = (source: string | null | undefined) => {
    const s = source ?? "university";
    const isProlific = s === "prolific";
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          isProlific
            ? "bg-amber-100 text-amber-800"
            : "bg-gray-100 text-gray-700"
        }`}
      >
        {isProlific ? "Prolific" : "University"}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const statusColors: Record<string, string> = {
      active: "bg-green-100 text-green-800",
      completed: "bg-gray-100 text-gray-800",
      recruited: "bg-yellow-100 text-yellow-800",
    };

    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          statusColors[status] || "bg-gray-100 text-gray-800"
        }`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Condition:
          </label>
          <select
            value={filterCondition}
            onChange={(e) => setFilterCondition(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="control">Control</option>
            <option value="experimental">Experimental</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Status:
          </label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="recruited">Recruited</option>
            <option value="excluded">Excluded</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">
            Source:
          </label>
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="university">University</option>
            <option value="prolific">Prolific</option>
          </select>
        </div>
        <div className="ml-auto text-sm text-gray-600">
          Showing {filteredParticipants.length} of {participants.length}{" "}
          participants
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => handleSort("participant_code")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Participant Code
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("condition_assigned")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Condition
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("recruitment_source" as SortField)}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Source
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("status")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Status
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("tasks_completed")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Tasks
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("session_duration_minutes")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Duration
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
              <th
                onClick={() => handleSort("last_activity")}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                <div className="flex items-center gap-2">
                  Last Activity
                  <ArrowUpDown className="w-4 h-4" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredParticipants.map((participant) => (
              <tr
                key={participant.id}
                onClick={() => router.push(`/admin/participants/${participant.id}`)}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {participant.participant_code}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getConditionBadge(participant.condition_assigned)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getSourceBadge(participant.recruitment_source)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(participant.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {participant.tasks_completed} / {participant.tasks_total}
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${
                          participant.tasks_total > 0
                            ? (participant.tasks_completed /
                                participant.tasks_total) *
                              100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatDuration(participant.session_duration_minutes)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatLastActivity(participant.last_activity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredParticipants.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">No participants match the selected filters</p>
          </div>
        )}
      </div>
    </div>
  );
}
