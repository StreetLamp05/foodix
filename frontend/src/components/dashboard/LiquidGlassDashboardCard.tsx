"use client";

import type { ReactNode } from "react";
import { useState } from "react";

interface LiquidGlassDashboardCardProps {
  title: string;
  children: ReactNode;
  isEditing?: boolean;
  dragHandleSlot?: ReactNode;
  glassVariant?: 'squircle' | 'liquid';
}

export default function LiquidGlassDashboardCard({
  title,
  children,
  isEditing = false,
  dragHandleSlot,
  glassVariant = 'squircle',
}: LiquidGlassDashboardCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  const containerStyle: React.CSSProperties = {
    background: "rgba(255, 255, 255, 0.05)",
    border: isHovered 
      ? "1px solid rgba(255, 255, 255, 0.4)" 
      : "1px solid rgba(255, 255, 255, 0.15)",
    borderRadius: glassVariant === 'squircle' ? "24px" : "32px",
    backdropFilter: `url(#${glassVariant === 'squircle' ? 'squircle' : 'liquid'}Filter)`,
    WebkitBackdropFilter: `url(#${glassVariant === 'squircle' ? 'squircle' : 'liquid'}Filter)`,
    boxShadow: isHovered
      ? "20px 25px 40px rgba(0,0,0,0.4), inset -3px -3px 8px rgba(255,255,255,0.1)"
      : "15px 20px 30px rgba(0,0,0,0.3), inset -2px -2px 6px rgba(255,255,255,0.05)",
    padding: "1.5rem",
    height: "100%",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    position: "relative",
    transition: "all 0.3s cubic-bezier(0.2, 0, 0.2, 1)",
    transform: isHovered ? "translateY(-2px) scale(1.01)" : "translateY(0) scale(1)",
    color: "white",
    textShadow: "0 1px 2px rgba(0,0,0,0.3)",
  };

  const headerStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "0.75rem",
    flexShrink: 0,
  };

  const titleStyle: React.CSSProperties = {
    fontSize: "1.1rem",
    fontWeight: 700,
    color: "rgba(255, 255, 255, 0.95)",
    margin: 0,
    letterSpacing: "0.025em",
    textShadow: "0 2px 4px rgba(0,0,0,0.8)",
  };

  const contentStyle: React.CSSProperties = {
    flex: 1,
    overflowY: "auto",
    minHeight: 0,
    color: "rgba(255, 255, 255, 0.9)",
    textShadow: "0 2px 4px rgba(0,0,0,0.6)",
  };

  return (
    <div
      style={containerStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div style={headerStyle}>
        <h3 style={titleStyle}>
          {title}
        </h3>
        {dragHandleSlot}
      </div>
      <div style={contentStyle}>
        {children}
      </div>
    </div>
  );
}