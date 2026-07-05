"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KPICardProps {
  title: string;
  value: string | number;
  format?: "number" | "currency" | "percentage" | "text";
  change?: number; // Percentage change
  changeLabel?: string; // e.g., "vs. last year"
  subtitle?: string; // Optional subtitle text
  icon?: React.ReactNode;
  loading?: boolean;
  decimals?: number;
  onClick?: () => void; // Click tracking handler
}

export default function KPICard({
  title,
  value,
  format = "number",
  change,
  changeLabel,
  subtitle,
  icon,
  loading = false,
  decimals = 0,
  onClick,
}: KPICardProps) {
  // Format value based on type
  const formatValue = (val: string | number): string => {
    // Handle text format - no parsing needed
    if (format === "text") {
      return typeof val === "string" ? val : String(val);
    }

    const numVal = typeof val === "string" ? parseFloat(val) : val;

    if (isNaN(numVal)) return typeof val === "string" ? val : "N/A";

    switch (format) {
      case "currency":
        if (numVal >= 1000000) {
          return `$${(numVal / 1000000).toFixed(1)}M`;
        } else if (numVal >= 1000) {
          return `$${(numVal / 1000).toFixed(1)}K`;
        }
        return `$${numVal.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;

      case "percentage":
        return `${numVal.toFixed(decimals)}%`;

      case "number":
      default:
        return numVal.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }
  };

  // Determine trend color and icon
  const getTrendInfo = () => {
    if (change === undefined || change === null) return null;

    const isPositive = change > 0;
    const isNegative = change < 0;
    const isNeutral = change === 0;

    return {
      color: isPositive ? "text-green-600" : isNegative ? "text-red-600" : "text-gray-600",
      bgColor: isPositive ? "bg-green-50" : isNegative ? "bg-red-50" : "bg-gray-50",
      icon: isPositive ? (
        <TrendingUp className="w-3 h-3" />
      ) : isNegative ? (
        <TrendingDown className="w-3 h-3" />
      ) : (
        <Minus className="w-3 h-3" />
      ),
      text: `${isPositive ? "+" : ""}${change.toFixed(1)}%`,
    };
  };

  const trendInfo = getTrendInfo();

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm animate-pulse">
        <div className="h-3 bg-gray-200 rounded w-1/2 mb-3"></div>
        <div className="h-6 bg-gray-200 rounded w-3/4 mb-1"></div>
        <div className="h-3 bg-gray-200 rounded w-1/3"></div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 p-3 shadow-sm hover:shadow-md transition-shadow ${onClick ? 'cursor-pointer hover:border-blue-300' : ''}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header with Icon */}
      <div className="flex items-center justify-between mb-1.5">
        <h3 className="text-xs font-medium text-gray-500">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2 mb-1">
        <p className="text-xl font-bold text-gray-900">{formatValue(value)}</p>
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-gray-500 mb-1">{subtitle}</p>
      )}

      {/* Trend Indicator */}
      {trendInfo && (
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-full ${trendInfo.bgColor}`}>
            <span className={trendInfo.color}>{trendInfo.icon}</span>
            <span className={`text-[10px] font-medium ${trendInfo.color}`}>
              {trendInfo.text}
            </span>
          </div>
          {changeLabel && (
            <span className="text-xs text-gray-500">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
