"use client";

import { useState, useEffect } from "react";
import { Calendar, ChevronDown } from "lucide-react";

export type TimePreset =
  | "this_month"
  | "last_month"
  | "this_quarter"
  | "last_quarter"
  | "this_half"
  | "last_half"
  | "this_year"
  | "last_year"
  | "ytd"
  | "custom";

export interface TimeRange {
  startDate: string;
  endDate: string;
  preset: TimePreset;
  label: string;
}

interface TimeRangeFilterProps {
  onChange: (range: TimeRange) => void;
  defaultPreset?: TimePreset;
}

export default function TimeRangeFilter({
  onChange,
  defaultPreset = "this_year"
}: TimeRangeFilterProps) {
  const [selectedPreset, setSelectedPreset] = useState<TimePreset>(defaultPreset);
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);

  // Calculate date ranges based on preset
  const getDateRange = (preset: TimePreset): { startDate: string; endDate: string; label: string } => {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth(); // 0-indexed

    switch (preset) {
      case "this_month": {
        const start = new Date(currentYear, currentMonth, 1);
        const end = new Date(currentYear, currentMonth + 1, 0);
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `This Month (${start.toLocaleDateString("en-US", { month: "short", year: "numeric" })})`
        };
      }

      case "last_month": {
        const start = new Date(currentYear, currentMonth - 1, 1);
        const end = new Date(currentYear, currentMonth, 0);
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `Last Month (${start.toLocaleDateString("en-US", { month: "short", year: "numeric" })})`
        };
      }

      case "this_quarter": {
        const quarterStartMonth = Math.floor(currentMonth / 3) * 3;
        const start = new Date(currentYear, quarterStartMonth, 1);
        const end = new Date(currentYear, quarterStartMonth + 3, 0);
        const quarter = Math.floor(currentMonth / 3) + 1;
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `This Quarter (Q${quarter} ${currentYear})`
        };
      }

      case "last_quarter": {
        const lastQuarterStartMonth = Math.floor((currentMonth - 3) / 3) * 3;
        const start = new Date(currentYear, lastQuarterStartMonth, 1);
        const end = new Date(currentYear, lastQuarterStartMonth + 3, 0);
        const quarter = Math.floor(lastQuarterStartMonth / 3) + 1;
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `Last Quarter (Q${quarter} ${start.getFullYear()})`
        };
      }

      case "this_half": {
        const halfStartMonth = currentMonth < 6 ? 0 : 6;
        const start = new Date(currentYear, halfStartMonth, 1);
        const end = new Date(currentYear, halfStartMonth + 6, 0);
        const half = halfStartMonth === 0 ? 1 : 2;
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `This Half (H${half} ${currentYear})`
        };
      }

      case "last_half": {
        const lastHalfStartMonth = currentMonth < 6 ? 6 : 0;
        const year = currentMonth < 6 ? currentYear - 1 : currentYear;
        const start = new Date(year, lastHalfStartMonth, 1);
        const end = new Date(year, lastHalfStartMonth + 6, 0);
        const half = lastHalfStartMonth === 0 ? 1 : 2;
        return {
          startDate: start.toISOString().split("T")[0],
          endDate: end.toISOString().split("T")[0],
          label: `Last Half (H${half} ${year})`
        };
      }

      case "this_year": {
        return {
          startDate: `${currentYear}-01-01`,
          endDate: `${currentYear}-12-31`,
          label: `This Year (${currentYear})`
        };
      }

      case "last_year": {
        return {
          startDate: `${currentYear - 1}-01-01`,
          endDate: `${currentYear - 1}-12-31`,
          label: `Last Year (${currentYear - 1})`
        };
      }

      case "ytd": {
        return {
          startDate: `${currentYear}-01-01`,
          endDate: now.toISOString().split("T")[0],
          label: `Year to Date (${currentYear})`
        };
      }

      case "custom": {
        return {
          startDate: customStartDate || `${currentYear}-01-01`,
          endDate: customEndDate || now.toISOString().split("T")[0],
          label: "Custom Range"
        };
      }

      default:
        return {
          startDate: `${currentYear}-01-01`,
          endDate: `${currentYear}-12-31`,
          label: `${currentYear}`
        };
    }
  };

  // Handle preset change
  const handlePresetChange = (preset: TimePreset) => {
    setSelectedPreset(preset);
    setShowDropdown(false);

    if (preset !== "custom") {
      const range = getDateRange(preset);
      onChange({
        ...range,
        preset
      });
    }
  };

  // Handle custom date change
  const handleCustomDateChange = () => {
    if (customStartDate && customEndDate) {
      const start = new Date(customStartDate);
      const end = new Date(customEndDate);
      const label = `${start.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })} - ${end.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;

      onChange({
        startDate: customStartDate,
        endDate: customEndDate,
        preset: "custom",
        label
      });
    }
  };

  // Initialize with default preset
  useEffect(() => {
    const range = getDateRange(defaultPreset);
    onChange({
      ...range,
      preset: defaultPreset
    });
  }, []);

  // Update when custom dates change
  useEffect(() => {
    if (selectedPreset === "custom" && customStartDate && customEndDate) {
      handleCustomDateChange();
    }
  }, [customStartDate, customEndDate]);

  const currentRange = getDateRange(selectedPreset);

  const presetOptions: { value: TimePreset; label: string; group: string }[] = [
    { value: "this_month", label: "This Month", group: "Monthly" },
    { value: "last_month", label: "Last Month", group: "Monthly" },
    { value: "this_quarter", label: "This Quarter", group: "Quarterly" },
    { value: "last_quarter", label: "Last Quarter", group: "Quarterly" },
    { value: "this_half", label: "This Half", group: "Semi-Annually" },
    { value: "last_half", label: "Last Half", group: "Semi-Annually" },
    { value: "this_year", label: "This Year", group: "Annually" },
    { value: "last_year", label: "Last Year", group: "Annually" },
    { value: "ytd", label: "Year to Date", group: "Special" },
    { value: "custom", label: "Custom Range", group: "Special" },
  ];

  // Group options
  const groupedOptions = presetOptions.reduce((acc, option) => {
    if (!acc[option.group]) {
      acc[option.group] = [];
    }
    acc[option.group].push(option);
    return acc;
  }, {} as Record<string, typeof presetOptions>);

  return (
    <div className="relative">
      {/* Dropdown Button */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
      >
        <Calendar className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">
          {currentRange.label}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showDropdown ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown Menu */}
      {showDropdown && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-[600px] overflow-y-auto">
            {Object.entries(groupedOptions).map(([group, options]) => (
              <div key={group} className="border-b border-gray-100 last:border-b-0">
                <div className="px-4 py-2 bg-gray-50">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {group}
                  </span>
                </div>
                {options.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handlePresetChange(option.value)}
                    className={`w-full text-left px-4 py-2 hover:bg-blue-50 transition-colors ${
                      selectedPreset === option.value
                        ? "bg-blue-50 text-blue-700 font-medium"
                        : "text-gray-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{option.label}</span>
                      {selectedPreset === option.value && (
                        <div className="w-2 h-2 bg-blue-600 rounded-full" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ))}

            {/* Custom Date Range Inputs */}
            {selectedPreset === "custom" && (
              <div className="p-4 bg-gray-50 border-t border-gray-200">
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={customStartDate}
                      onChange={(e) => setCustomStartDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={customEndDate}
                      onChange={(e) => setCustomEndDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
