/**
 * Health-check service.
 *
 * Calls the backend `GET /health` endpoint through the typed API client and
 * returns the parsed, typed response. UI code uses this to display backend
 * connectivity status; it must not call `fetch` directly.
 */

import { apiFetch } from "@/lib/apiClient";
import type { HealthResponse } from "@/types/api";

/**
 * Fetch backend health.
 *
 * Resolves with the typed `HealthResponse` on success; rejects with `ApiError`
 * when the backend is unreachable or returns a non-2xx status.
 */
export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { cache: "no-store" });
}
