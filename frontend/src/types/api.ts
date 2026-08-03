/**
 * Shared API type definitions.
 *
 * These mirror the backend Pydantic response models. During the scaffold
 * phase only the health-check contract exists; accounting types are added in
 * later feature branches.
 */

/** Response shape of the backend `GET /health` endpoint. */
export interface HealthResponse {
  status: string;
  service: string;
}
