"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiUrl } from "@/lib/api";
import DashboardShell from "@/components/dashboard/DashboardShell";

type HealthStatus = {
  status: string;
  database: string;
  timestamp: string;
} | null;

export default function Home() {
  const [health, setHealth] = useState<HealthStatus>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((res) => res.json())
      .then((data) => {
        setHealth(data);
        setError(false);
      })
      .catch(() => setError(true));
  }, []);

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "1rem 1.5rem",
          borderBottom: "var(--card-border)",
          background: "var(--card-bg)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>
            Inventory Health Monitor
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: error
                  ? "var(--color-danger)"
                  : health
                    ? "var(--color-success)"
                    : "var(--color-warning)",
              }}
            />
            <span style={{ fontSize: "0.8rem", color: "var(--chart-text)" }}>
              {error
                ? "cant reach backend :/"
                : health
                  ? `${health.status}`
                  : "Connecting..."}
            </span>
          </div>
        </div>

        <Link
          href="/query"
          style={{
            background: "var(--btn-bg)",
            color: "var(--btn-color)",
            padding: "0.4rem 0.75rem",
            borderRadius: "var(--btn-radius)",
            fontSize: "0.85rem",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Query Inventory
        </Link>
      </div>

      {/* Dashboard */}
      <DashboardShell restaurantId={1} restaurantName="Dashboard" />
    </div>
  );
}
