"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchTrends } from "@/lib/dashboard-api";
import type { TrendDay } from "@/lib/types/dashboard";

interface TrafficCalendarViewProps {
  restaurantId: number;
}

type DayCell = {
  isoDate: string;
  dayOfMonth: number;
  inCurrentMonth: boolean;
  isToday: boolean;
  holidayName: string | null;
  predictedCovers: number;
  isHeavyTraffic: boolean;
};

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function TrafficCalendarView({ restaurantId }: TrafficCalendarViewProps) {
  const [anchorMonth, setAnchorMonth] = useState(() => startOfMonth(new Date()));
  const [trends, setTrends] = useState<TrendDay[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchTrends(restaurantId, 180)
      .then((rows) => {
        if (cancelled) return;
        setTrends(rows);
        setError(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [restaurantId]);

  const holidayMap = useMemo(
    () => buildUSHolidayMap(anchorMonth.getFullYear()),
    [anchorMonth]
  );

  const weekdayAverages = useMemo(() => {
    const sums = Array<number>(7).fill(0);
    const counts = Array<number>(7).fill(0);

    for (const row of trends ?? []) {
      const covers = Number(row.total_covers ?? 0);
      if (!Number.isFinite(covers)) continue;
      const dow = new Date(`${row.log_date}T00:00:00`).getDay();
      sums[dow] += covers;
      counts[dow] += 1;
    }

    return sums.map((sum, dow) => (counts[dow] > 0 ? sum / counts[dow] : 0));
  }, [trends]);

  const fallbackAverage = useMemo(() => {
    const values = weekdayAverages.filter((v) => v > 0);
    if (values.length === 0) return 0;
    return values.reduce((a, b) => a + b, 0) / values.length;
  }, [weekdayAverages]);

  const heavyThreshold = useMemo(() => {
    const values = weekdayAverages.filter((v) => v > 0);
    if (values.length === 0) return 0;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
    const stdDev = Math.sqrt(variance);
    return mean + stdDev * 0.5;
  }, [weekdayAverages]);

  const cells = useMemo(() => {
    return buildMonthCells({
      anchorMonth,
      today: new Date(),
      holidayMap,
      weekdayAverages,
      fallbackAverage,
      heavyThreshold,
    });
  }, [anchorMonth, fallbackAverage, heavyThreshold, holidayMap, weekdayAverages]);

  if (error) {
    return <p style={{ color: "var(--color-danger)" }}>Failed to load calendar data</p>;
  }

  if (!trends) {
    return <Skeleton />;
  }

  return (
    <div
      style={{
        background: "var(--card-bg)",
        border: "var(--card-border)",
        borderRadius: "var(--card-radius)",
        boxShadow: "var(--card-shadow)",
        padding: "1rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.75rem",
          gap: "0.5rem",
        }}
      >
        <button
          onClick={() => setAnchorMonth(addMonths(anchorMonth, -1))}
          style={navButtonStyle}
        >
          Previous
        </button>
        <h2 style={{ margin: 0, fontSize: "1.05rem" }}>
          {anchorMonth.toLocaleString("en-US", { month: "long", year: "numeric" })}
        </h2>
        <button
          onClick={() => setAnchorMonth(addMonths(anchorMonth, 1))}
          style={navButtonStyle}
        >
          Next
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          fontSize: "0.8rem",
          color: "var(--chart-text)",
          marginBottom: "0.75rem",
        }}
      >
        <LegendChip label="Predicted Heavy Traffic" color="#f59e0b" />
        <LegendChip label="Holiday" color="#3b82f6" />
        <LegendChip label="Both" color="#8b5cf6" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: "0.4rem" }}>
        {DAYS_OF_WEEK.map((day) => (
          <div key={day} style={weekdayHeaderStyle}>
            {day}
          </div>
        ))}
        {cells.map((cell) => (
          <div
            key={cell.isoDate}
            style={dayCellStyle(cell)}
            title={[
              `Predicted covers: ${Math.round(cell.predictedCovers)}`,
              cell.holidayName ? `Holiday: ${cell.holidayName}` : "",
              cell.isHeavyTraffic ? "Predicted heavy traffic day" : "",
            ]
              .filter(Boolean)
              .join("\n")}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "0.4rem" }}>
              <span style={{ fontWeight: cell.isToday ? 700 : 600 }}>{cell.dayOfMonth}</span>
              <span style={{ fontSize: "0.72rem", opacity: 0.85 }}>{Math.round(cell.predictedCovers)}</span>
            </div>
            {cell.holidayName && (
              <div
                style={{
                  marginTop: "0.2rem",
                  fontSize: "0.68rem",
                  lineHeight: 1.2,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {cell.holidayName}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function buildMonthCells({
  anchorMonth,
  today,
  holidayMap,
  weekdayAverages,
  fallbackAverage,
  heavyThreshold,
}: {
  anchorMonth: Date;
  today: Date;
  holidayMap: Map<string, string>;
  weekdayAverages: number[];
  fallbackAverage: number;
  heavyThreshold: number;
}): DayCell[] {
  const monthStart = startOfMonth(anchorMonth);
  const monthEnd = endOfMonth(anchorMonth);
  const gridStart = addDays(monthStart, -monthStart.getDay());
  const daysInGrid = 42;
  const todayIso = toIsoDate(today);

  const cells: DayCell[] = [];
  for (let i = 0; i < daysInGrid; i += 1) {
    const date = addDays(gridStart, i);
    const isoDate = toIsoDate(date);
    const dow = date.getDay();
    const predictedCovers = weekdayAverages[dow] > 0 ? weekdayAverages[dow] : fallbackAverage;
    const holidayName = holidayMap.get(isoDate) ?? null;
    const isHeavyTraffic = predictedCovers > 0 && predictedCovers >= heavyThreshold;

    cells.push({
      isoDate,
      dayOfMonth: date.getDate(),
      inCurrentMonth: date >= monthStart && date <= monthEnd,
      isToday: isoDate === todayIso,
      holidayName,
      predictedCovers,
      isHeavyTraffic,
    });
  }
  return cells;
}

function LegendChip({ label, color }: { label: string; color: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 999,
          display: "inline-block",
          background: color,
        }}
      />
      {label}
    </span>
  );
}

function dayCellStyle(cell: DayCell): React.CSSProperties {
  const hasHoliday = Boolean(cell.holidayName);
  const hasHeavy = cell.isHeavyTraffic;
  const accent = hasHoliday && hasHeavy ? "#8b5cf6" : hasHoliday ? "#3b82f6" : hasHeavy ? "#f59e0b" : "rgba(0,0,0,0.08)";
  const background = hasHoliday && hasHeavy
    ? "rgba(139,92,246,0.14)"
    : hasHoliday
      ? "rgba(59,130,246,0.12)"
      : hasHeavy
        ? "rgba(245,158,11,0.12)"
        : "var(--background)";

  return {
    minHeight: 84,
    border: `1px solid ${accent}`,
    borderRadius: 10,
    padding: "0.35rem 0.45rem",
    background,
    color: cell.inCurrentMonth ? "var(--foreground)" : "var(--chart-text)",
    opacity: cell.inCurrentMonth ? 1 : 0.65,
    outline: cell.isToday ? "2px solid var(--btn-bg)" : "none",
  };
}

const weekdayHeaderStyle: React.CSSProperties = {
  fontSize: "0.76rem",
  fontWeight: 700,
  color: "var(--chart-text)",
  textAlign: "center",
  paddingBottom: "0.2rem",
};

const navButtonStyle: React.CSSProperties = {
  border: "var(--card-border)",
  background: "transparent",
  color: "var(--foreground)",
  borderRadius: "var(--btn-radius)",
  padding: "0.35rem 0.65rem",
  fontSize: "0.8rem",
  cursor: "pointer",
};

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function addDays(date: Date, days: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

function addMonths(date: Date, months: number) {
  return new Date(date.getFullYear(), date.getMonth() + months, 1);
}

function toIsoDate(date: Date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function buildUSHolidayMap(year: number) {
  const holidays = new Map<string, string>();

  holidays.set(toIsoDate(new Date(year, 0, 1)), "New Year's Day");
  holidays.set(toIsoDate(getNthWeekdayOfMonth(year, 0, 1, 3)), "Martin Luther King Jr. Day");
  holidays.set(toIsoDate(getNthWeekdayOfMonth(year, 1, 1, 3)), "Presidents' Day");
  holidays.set(toIsoDate(getLastWeekdayOfMonth(year, 4, 1)), "Memorial Day");
  holidays.set(toIsoDate(new Date(year, 5, 19)), "Juneteenth");
  holidays.set(toIsoDate(new Date(year, 6, 4)), "Independence Day");
  holidays.set(toIsoDate(getNthWeekdayOfMonth(year, 8, 1, 1)), "Labor Day");
  holidays.set(toIsoDate(getNthWeekdayOfMonth(year, 9, 1, 2)), "Columbus Day");
  holidays.set(toIsoDate(new Date(year, 10, 11)), "Veterans Day");
  holidays.set(toIsoDate(getNthWeekdayOfMonth(year, 10, 4, 4)), "Thanksgiving");
  holidays.set(toIsoDate(new Date(year, 11, 25)), "Christmas Day");

  return holidays;
}

function getNthWeekdayOfMonth(year: number, month: number, weekday: number, nth: number) {
  const first = new Date(year, month, 1);
  const dayOffset = (weekday - first.getDay() + 7) % 7;
  return new Date(year, month, 1 + dayOffset + (nth - 1) * 7);
}

function getLastWeekdayOfMonth(year: number, month: number, weekday: number) {
  const lastDay = new Date(year, month + 1, 0);
  const dayOffset = (lastDay.getDay() - weekday + 7) % 7;
  return new Date(year, month + 1, 0 - dayOffset);
}

function Skeleton() {
  return (
    <div
      style={{
        height: 420,
        background: "var(--background)",
        borderRadius: "var(--card-radius)",
        animation: "pulse 1.5s ease-in-out infinite",
      }}
    />
  );
}
