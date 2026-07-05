"use client";

import { useState, useEffect } from "react";
import { Calendar, ChevronDown, ChevronRight } from "lucide-react";

export type TimeGranularity = "annual" | "quarterly" | "monthly" | "custom";

export interface TimeRange {
  startDate: string;
  endDate: string;
  granularity: TimeGranularity;
  label: string;
}

interface TimeRangeFilterProps {
  onChange: (range: TimeRange) => void;
  defaultGranularity?: TimeGranularity;
}

export default function TimeRangeFilter({
  onChange,
  defaultGranularity = "annual"
}: TimeRangeFilterProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [step, setStep] = useState<"granularity" | "year" | "period">("granularity");
  const [selectedGranularity, setSelectedGranularity] = useState<TimeGranularity>(defaultGranularity);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string>("");
  const [currentLabel, setCurrentLabel] = useState<string>("This Year (2024)");

  // Custom date range state
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth(); // 0-indexed

  // Actual data range: May 2022 - June 2025
  const DATA_START_YEAR = 2022;
  const DATA_END_YEAR = 2025;

  // Helper function to format date as YYYY-MM-DD without timezone conversion
  // Using toISOString() causes timezone issues (e.g., Apr 1 local -> Mar 31 UTC)
  const formatDateLocal = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  // Get available years based on actual data
  const getAvailableYears = (): { value: number; label: string }[] => {
    const years = [];
    const endYear = Math.min(DATA_END_YEAR, currentYear);

    for (let year = endYear; year >= DATA_START_YEAR; year--) {
      years.push({
        value: year,
        label: year === currentYear ? `${year} (Current)` : `${year}`
      });
    }
    return years;
  };

  // Get available periods based on granularity and selected year
  const getPeriodOptions = (granularity: TimeGranularity, year?: number | null): { value: string; label: string }[] => {
    switch (granularity) {
      case "annual": {
        const options = [];
        const endYear = Math.min(DATA_END_YEAR, currentYear);

        // Add YTD option first
        options.push({ value: "ytd", label: `Year to Date (${currentYear})` });

        // Add all available years
        for (let y = endYear; y >= DATA_START_YEAR; y--) {
          const isCurrent = y === currentYear;
          const isLast = y === currentYear - 1;
          let label = `${y}`;
          if (isCurrent) label += " (This Year)";
          else if (isLast) label += " (Last Year)";

          options.push({ value: `${y}`, label });
        }

        return options;
      }

      case "quarterly": {
        if (!year) return [];
        const quarters = [];
        const currentQuarter = Math.floor(currentMonth / 3) + 1;

        // Show all 4 quarters for the selected year
        for (let q = 1; q <= 4; q++) {
          const isCurrent = year === currentYear && q === currentQuarter;
          quarters.push({
            value: `Q${q}`,
            label: `Q${q}${isCurrent ? " (Current)" : ""}`
          });
        }

        return quarters.reverse(); // Show Q4, Q3, Q2, Q1
      }

      case "monthly": {
        if (!year) return [];
        const months = [];
        const monthNames = [
          "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"
        ];

        // Show all 12 months for the selected year
        for (let m = 0; m < 12; m++) {
          const isCurrent = year === currentYear && m === currentMonth;
          months.push({
            value: `${String(m + 1).padStart(2, "0")}`,
            label: `${monthNames[m]}${isCurrent ? " (Current)" : ""}`
          });
        }

        return months.reverse(); // Show December to January
      }

      case "custom":
        return [];

      default:
        return [];
    }
  };

  // Calculate date range from period selection
  const calculateDateRange = (granularity: TimeGranularity, period: string, year?: number | null): { startDate: string; endDate: string; label: string } => {
    switch (granularity) {
      case "annual": {
        if (period === "ytd") {
          return {
            startDate: `${currentYear}-01-01`,
            endDate: formatDateLocal(now),
            label: `Year to Date (${currentYear})`
          };
        }

        const yearNum = parseInt(period);
        return {
          startDate: `${yearNum}-01-01`,
          endDate: `${yearNum}-12-31`,
          label: yearNum === currentYear ? `This Year (${yearNum})` : `Year ${yearNum}`
        };
      }

      case "quarterly": {
        if (!year) return { startDate: "", endDate: "", label: "" };

        const quarter = parseInt(period.replace("Q", ""));
        const startMonth = (quarter - 1) * 3;

        const startDate = new Date(year, startMonth, 1);
        const endDate = new Date(year, startMonth + 3, 0);

        return {
          startDate: formatDateLocal(startDate),
          endDate: formatDateLocal(endDate),
          label: `Q${quarter} ${year}`
        };
      }

      case "monthly": {
        if (!year) return { startDate: "", endDate: "", label: "" };

        const monthNum = parseInt(period);

        const startDate = new Date(year, monthNum - 1, 1);
        const endDate = new Date(year, monthNum, 0);

        const monthNames = [
          "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"
        ];

        return {
          startDate: formatDateLocal(startDate),
          endDate: formatDateLocal(endDate),
          label: `${monthNames[monthNum - 1]} ${year}`
        };
      }

      case "custom": {
        if (customStartDate && customEndDate) {
          const start = new Date(customStartDate);
          const end = new Date(customEndDate);
          return {
            startDate: customStartDate,
            endDate: customEndDate,
            label: `${start.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })} - ${end.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
          };
        }
        return {
          startDate: `${currentYear}-01-01`,
          endDate: formatDateLocal(now),
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

  // Handle granularity selection
  const handleGranularitySelect = (granularity: TimeGranularity) => {
    setSelectedGranularity(granularity);
    setSelectedYear(null);
    setSelectedPeriod("");

    if (granularity === "custom") {
      setStep("period");
    } else if (granularity === "annual") {
      // Annual goes directly to period selection (years)
      setStep("period");
    } else {
      // Quarterly and Monthly need year selection first
      setStep("year");
    }
  };

  // Handle year selection (for quarterly/monthly)
  const handleYearSelect = (year: number) => {
    setSelectedYear(year);
    setStep("period");
  };

  // Handle period selection
  const handlePeriodSelect = (period: string) => {
    setSelectedPeriod(period);
    const range = calculateDateRange(selectedGranularity, period, selectedYear);
    setCurrentLabel(range.label);

    onChange({
      ...range,
      granularity: selectedGranularity
    });

    setShowDropdown(false);
    setStep("granularity");
    setSelectedYear(null);
  };

  // Handle custom date changes
  useEffect(() => {
    if (selectedGranularity === "custom" && customStartDate && customEndDate) {
      const range = calculateDateRange("custom", "");
      setCurrentLabel(range.label);

      onChange({
        ...range,
        granularity: "custom"
      });
    }
  }, [customStartDate, customEndDate]);

  // Initialize with default (2024 for full year data)
  useEffect(() => {
    const defaultYear = 2024; // Use 2024 as it has complete data
    const defaultRange = calculateDateRange("annual", `${defaultYear}`);
    setCurrentLabel(defaultRange.label);
    onChange({
      ...defaultRange,
      granularity: "annual"
    });
  }, []);

  // Handle back navigation
  const handleBack = () => {
    if (step === "period" && (selectedGranularity === "quarterly" || selectedGranularity === "monthly")) {
      // Go back to year selection for quarterly/monthly
      setStep("year");
      setSelectedPeriod("");
    } else if (step === "year") {
      // Go back to granularity selection
      setStep("granularity");
      setSelectedYear(null);
    } else {
      // Default: go back to granularity
      setStep("granularity");
      setSelectedPeriod("");
    }
  };

  // Handle dropdown close
  const handleClose = () => {
    setShowDropdown(false);
    setStep("granularity");
  };

  const granularityOptions = [
    { value: "annual" as TimeGranularity, label: "Annual", description: "View data by year" },
    { value: "quarterly" as TimeGranularity, label: "Quarterly", description: "View data by quarter" },
    { value: "monthly" as TimeGranularity, label: "Monthly", description: "View data by month" },
    { value: "custom" as TimeGranularity, label: "Custom Range", description: "Select custom dates" },
  ];

  return (
    <div className="relative">
      {/* Dropdown Button */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
      >
        <Calendar className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">
          {currentLabel}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showDropdown ? "rotate-180" : ""}`} />
      </button>

      {/* Dropdown Menu */}
      {showDropdown && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={handleClose}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-96 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              {(step === "year" || step === "period") && (
                <button
                  onClick={handleBack}
                  className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
                >
                  <ChevronRight className="w-4 h-4 rotate-180" />
                  Back
                </button>
              )}
              <h3 className="text-sm font-semibold text-gray-900">
                {step === "granularity" && "Select Time Granularity"}
                {step === "year" && "Select Year"}
                {step === "period" && selectedGranularity === "annual" && "Select Year"}
                {step === "period" && selectedGranularity === "quarterly" && "Select Quarter"}
                {step === "period" && selectedGranularity === "monthly" && "Select Month"}
                {step === "period" && selectedGranularity === "custom" && "Custom Date Range"}
              </h3>
              {step === "granularity" && <div className="w-12" />}
            </div>

            {/* Content */}
            <div className="max-h-[400px] overflow-y-auto">
              {step === "granularity" ? (
                // Step 1: Granularity Selection
                <div className="p-2">
                  {granularityOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => handleGranularitySelect(option.value)}
                      className="w-full text-left px-4 py-3 rounded-lg hover:bg-blue-50 transition-colors group"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-gray-900 group-hover:text-blue-700">
                            {option.label}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {option.description}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : step === "year" ? (
                // Step 2: Year Selection (for quarterly/monthly)
                <div className="p-2">
                  {getAvailableYears().map((yearOption) => (
                    <button
                      key={yearOption.value}
                      onClick={() => handleYearSelect(yearOption.value)}
                      className="w-full text-left px-4 py-2.5 rounded-lg hover:bg-blue-50 transition-colors text-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm">{yearOption.label}</span>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : selectedGranularity === "custom" ? (
                // Step 2: Custom Date Range
                <div className="p-4">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-2">
                        Start Date
                      </label>
                      <input
                        type="date"
                        value={customStartDate}
                        onChange={(e) => setCustomStartDate(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-2">
                        End Date
                      </label>
                      <input
                        type="date"
                        value={customEndDate}
                        onChange={(e) => setCustomEndDate(e.target.value)}
                        min={customStartDate}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    {customStartDate && customEndDate && (
                      <button
                        onClick={() => {
                          handlePeriodSelect("custom");
                        }}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                      >
                        Apply Custom Range
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                // Step 3: Period Selection (annual/quarterly/monthly)
                <div className="p-2">
                  {getPeriodOptions(selectedGranularity, selectedYear).map((option) => (
                    <button
                      key={option.value}
                      onClick={() => handlePeriodSelect(option.value)}
                      className={`w-full text-left px-4 py-2.5 rounded-lg hover:bg-blue-50 transition-colors ${
                        selectedPeriod === option.value ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm">{option.label}</span>
                        {selectedPeriod === option.value && (
                          <div className="w-2 h-2 bg-blue-600 rounded-full" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
