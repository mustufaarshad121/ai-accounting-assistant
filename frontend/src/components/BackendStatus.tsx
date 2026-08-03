"use client";

/**
 * BackendStatus — client component that probes backend connectivity.
 *
 * On mount it calls the health service and renders one of three states:
 *  - "Checking backend…" while the request is in flight,
 *  - "Backend connected" when `GET /health` succeeds,
 *  - "Backend unavailable" on any error.
 *
 * This is the frontend half of the scaffold's end-to-end smoke check. It
 * contains no accounting logic.
 */

import { useEffect, useState } from "react";
import { getHealth } from "@/services/healthService";

type ConnectionState = "loading" | "connected" | "unavailable";

interface StatusView {
  label: string;
  dotClass: string;
  textClass: string;
}

const VIEWS: Record<ConnectionState, StatusView> = {
  loading: {
    label: "Checking backend…",
    dotClass: "bg-amber-400 animate-pulse",
    textClass: "text-amber-700 dark:text-amber-400",
  },
  connected: {
    label: "Backend connected",
    dotClass: "bg-emerald-500",
    textClass: "text-emerald-700 dark:text-emerald-400",
  },
  unavailable: {
    label: "Backend unavailable",
    dotClass: "bg-rose-500",
    textClass: "text-rose-700 dark:text-rose-400",
  },
};

export default function BackendStatus() {
  const [state, setState] = useState<ConnectionState>("loading");
  const [service, setService] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    getHealth()
      .then((data) => {
        if (!active) return;
        setService(data.service);
        setState(data.status === "ok" ? "connected" : "unavailable");
      })
      .catch(() => {
        if (active) setState("unavailable");
      });

    return () => {
      active = false;
    };
  }, []);

  const view = VIEWS[state];

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-black/10 dark:border-white/15 px-3 py-1.5 text-sm">
      <span
        aria-hidden="true"
        className={`h-2.5 w-2.5 rounded-full ${view.dotClass}`}
      />
      <span className={`font-medium ${view.textClass}`}>{view.label}</span>
      {state === "connected" && service ? (
        <span className="text-black/50 dark:text-white/50">· {service}</span>
      ) : null}
    </div>
  );
}
