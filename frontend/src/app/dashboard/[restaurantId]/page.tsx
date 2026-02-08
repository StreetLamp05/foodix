"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchRestaurant } from "@/lib/dashboard-api";
import DashboardShell from "@/components/dashboard/DashboardShell";
import type { Restaurant } from "@/lib/types/dashboard";

export default function DashboardPage() {
  const params = useParams<{ restaurantId: string }>();
  const restaurantId = Number(params.restaurantId);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (isNaN(restaurantId)) {
      setError(true);
      return;
    }
    fetchRestaurant(restaurantId)
      .then(setRestaurant)
      .catch(() => setError(true));
  }, [restaurantId]);

  if (error) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Restaurant not found</h1>
        <Link
          href="/"
          style={{
            display: "inline-block",
            marginTop: "1rem",
            color: "var(--btn-bg)",
            textDecoration: "underline",
          }}
        >
          Back to home
        </Link>
      </div>
    );
  }

  if (!restaurant) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <div style={{ fontSize: "1rem", color: "var(--chart-text)" }}>
          Loading dashboard...
        </div>
      </div>
    );
  }

  return (
    <>
      <div style={{ padding: "1rem 1.5rem 0" }}>
        <Link
          href="/"
          style={{
            fontSize: "0.85rem",
            color: "var(--chart-text)",
            textDecoration: "none",
          }}
        >
          &larr; All Restaurants
        </Link>
      </div>
      <DashboardShell
        restaurantId={restaurantId}
        restaurantName={restaurant.restaurant_name}
      />
    </>
  );
}
