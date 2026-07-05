"use client";

import { MessageSquareText } from "lucide-react";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
}

export default function Logo({ size = "md", showSubtitle = true }: LogoProps) {
  const sizeClasses = {
    sm: {
      container: "gap-2",
      icon: "w-6 h-6",
      text: "text-base",
      subtitle: "text-xs",
    },
    md: {
      container: "gap-2.5",
      icon: "w-8 h-8",
      text: "text-lg",
      subtitle: "text-xs",
    },
    lg: {
      container: "gap-3",
      icon: "w-10 h-10",
      text: "text-2xl",
      subtitle: "text-sm",
    },
  };

  const classes = sizeClasses[size];

  return (
    <div className="flex items-center">
      {/* Logo Icon */}
      <div className="flex items-center gap-2.5">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-1.5 shadow-md">
          <MessageSquareText className={`${classes.icon} text-white`} strokeWidth={2.5} />
        </div>

        {/* Logo Text */}
        <div className="flex flex-col">
          <h2 className={`${classes.text} font-bold tracking-tight`}>
            <span className="bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">
              Talk2Data
            </span>
          </h2>
          {showSubtitle && (
            <p className={`${classes.subtitle} text-gray-500 font-medium -mt-0.5`}>
              AI-Powered Analytics
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
