/**
 * Centralized frontend configuration.
 *
 * The backend base URL is read from the public environment variable
 * `NEXT_PUBLIC_API_URL`. It must never be hard-coded inside components —
 * import `API_BASE_URL` from here instead.
 *
 * Only `NEXT_PUBLIC_*` variables are exposed to the browser. Do not place
 * secrets here.
 */

const DEFAULT_API_URL = "http://localhost:8000";

/** Base URL of the FastAPI backend (e.g. http://localhost:8000). */
export const API_BASE_URL: string = (
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL
).replace(/\/+$/, "");
