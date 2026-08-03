/**
 * Typed API client foundation.
 *
 * A single thin wrapper around `fetch` that:
 *  - prefixes requests with the configured backend base URL,
 *  - always requests/accepts JSON,
 *  - raises a typed `ApiError` on non-2xx responses,
 *  - returns the parsed, generically-typed JSON body.
 *
 * Feature branches build their service functions on top of this client so no
 * component talks to `fetch` (or a hard-coded URL) directly.
 */

import { API_BASE_URL } from "@/config/env";

/** Error thrown for non-2xx responses or transport failures. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON-serializable request body. */
  body?: unknown;
}

/**
 * Perform a typed JSON request against the backend.
 *
 * @typeParam T - expected shape of the parsed JSON response.
 * @param path - path beginning with "/" (e.g. "/health").
 */
export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, headers, ...rest } = options;
  const url = `${API_BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    // Network / DNS / CORS failures never reach a status code.
    throw new ApiError(`Network error contacting backend at ${url}`, 0);
  }

  if (!response.ok) {
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}
