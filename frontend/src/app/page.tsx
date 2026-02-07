"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";

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
    <div className="flex min-h-screen flex-col items-center justify-center gap-8">
      <h1 className="text-4xl font-bold">Inventory Health Monitor</h1>
        <div className="flex items-center gap-8">
            <div
              className={`h-3 w-3 rounded-full ${
                error
                  ? "bg-red-500"
                  : health
                    ? "bg-green-500"
                    : "bg-yellow-500 animate-pulse"
              }`}
            />
            <span className="text-sm">
              {error
                ? "cant reach backend :/"
                : health
                  ? `Backend ${health.status} — DB ${health.database}`
                  : "Connecting..."}
            </span>
        </div>
      </div>
  );
}
