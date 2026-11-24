/**
 * Strongly typed HTTP client connecting the Obsidian plugin to the Spindle FastAPI backend.
 * Uses Obsidian's native `requestUrl` when available, falling back to global `fetch` for headless testing.
 */

import type { RequestUrlParam } from "obsidian";
import {
  CommitSuggestionRequest,
  CommitSuggestionResponse,
  EditSuggestionRequest,
  SpindleSettings,
  StoryOverview,
  Suggestion,
  SuggestionType,
  SyncFileInput,
  VaultSyncResponse,
} from "../types";

// Safely obtain Obsidian's runtime requestUrl if running inside Obsidian desktop
function getObsidianRequestUrl(): ((params: RequestUrlParam) => Promise<any>) | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const obs = require("obsidian");
    return typeof obs?.requestUrl === "function" ? obs.requestUrl : null;
  } catch {
    return null;
  }
}

export class BackendClient {
  private settings: SpindleSettings;

  constructor(settings: SpindleSettings) {
    this.settings = settings;
  }

  public updateSettings(settings: SpindleSettings): void {
    this.settings = settings;
  }

  private get baseUrl(): string {
    return this.settings.backendUrl.replace(/\/+$/, "");
  }

  private get headers(): Record<string, string> {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (this.settings.projectId) {
      h["X-Project-ID"] = this.settings.projectId;
    }
    return h;
  }

  private async request<T>(
    path: string,
    method: "GET" | "POST" | "PUT" | "DELETE" = "GET",
    body?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = this.headers;

    // Use Obsidian's requestUrl if available in runtime
    const obsidianRequest = getObsidianRequestUrl();
    if (obsidianRequest) {
      const params: RequestUrlParam = {
        url,
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      };

      try {
        const res = await obsidianRequest(params);
        if (res.status >= 400) {
          const detail = res.json?.detail || res.text || `HTTP ${res.status}`;
          throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        return res.json as T;
      } catch (err: any) {
        if (err.status) {
          const detail = err.json?.detail || err.message || `HTTP ${err.status}`;
          throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        throw err;
      }
    }

    // Fallback for tests running outside Obsidian environment
    const resp = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const errorJson = await resp.json();
        detail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        detail = await resp.text();
      }
      throw new Error(detail);
    }

    return (await resp.json()) as T;
  }

  /**
   * Check connection to backend health endpoint.
   */
  public async checkHealth(): Promise<{ status: string; environment?: string }> {
    return this.request<{ status: string; environment?: string }>("/health", "GET");
  }

  /**
   * Push vault files to backend for ingestion and indexing.
   */
  public async syncVault(files: SyncFileInput[]): Promise<VaultSyncResponse> {
    return this.request<VaultSyncResponse>("/api/v1/vault/sync", "POST", { files });
  }

  /**
   * Fetch current vault ingestion status.
   */
  public async getVaultStatus(): Promise<{
    project_id: string;
    total_documents: number;
    last_indexed_at?: string;
  }> {
    return this.request("/api/v1/vault/status", "GET");
  }

  /**
   * Fetch project story overview metrics (characters, events, locations, constraints, unresolved threads).
   */
  public async getStoryOverview(): Promise<StoryOverview> {
    return this.request<StoryOverview>("/api/v1/story/overview", "GET");
  }

  /**
   * Generate a plot point suggestion.
   */
  public async generatePlotPoint(payload: {
    request: string;
    narrative_position?: number;
    characters?: string[];
  }): Promise<Suggestion> {
    return this.request<Suggestion>("/api/v1/generate/plot-point", "POST", payload);
  }

  /**
   * Generate a canon-consistent side story suggestion.
   */
  public async generateSideStory(payload: {
    request: string;
    narrative_position?: number;
    characters?: string[];
  }): Promise<Suggestion> {
    return this.request<Suggestion>("/api/v1/generate/side-story", "POST", payload);
  }

  /**
   * Run continuity analysis over story state.
   */
  public async generateContinuityAnalysis(payload: {
    request: string;
    narrative_position?: number;
    characters?: string[];
  }): Promise<Suggestion> {
    return this.request<Suggestion>("/api/v1/generate/continuity-analysis", "POST", payload);
  }

  /**
   * Explore and synthesize multiple divergent narrative branches without requiring a prompt.
   */
  public async exploreBranches(payload: {
    narrative_position?: number;
    branch_id?: string;
    target_characters?: string[];
    branch_count?: number;
  }): Promise<Suggestion[]> {
    return this.request<Suggestion[]>("/api/v1/generate/explore-branches", "POST", payload);
  }

  /**
   * List suggestions for the active project.
   */
  public async listSuggestions(filter?: {
    status?: string;
    type?: SuggestionType;
  }): Promise<Suggestion[]> {
    const params = new URLSearchParams();
    if (filter?.status) params.set("status", filter.status);
    if (filter?.type) params.set("type", filter.type);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.request<Suggestion[]>(`/api/v1/suggestions${qs}`, "GET");
  }

  /**
   * Retrieve a specific suggestion with validation results.
   */
  public async getSuggestion(id: string): Promise<Suggestion> {
    return this.request<Suggestion>(`/api/v1/suggestions/${id}`, "GET");
  }

  /**
   * Approve a suggestion.
   */
  public async approveSuggestion(id: string, notes?: string): Promise<Suggestion> {
    return this.request<Suggestion>(`/api/v1/suggestions/${id}/approve`, "POST", { notes });
  }

  /**
   * Reject a suggestion with mandatory rationale.
   */
  public async rejectSuggestion(id: string, reason: string): Promise<Suggestion> {
    return this.request<Suggestion>(`/api/v1/suggestions/${id}/reject`, "POST", { reason });
  }

  /**
   * Edit a suggestion and preserve historical revision.
   */
  public async editSuggestion(id: string, payload: EditSuggestionRequest): Promise<Suggestion> {
    return this.request<Suggestion>(`/api/v1/suggestions/${id}/edit`, "PUT", payload);
  }

  /**
   * Non-destructively commit an approved suggestion to vault canon.
   */
  public async commitSuggestion(
    id: string,
    payload?: CommitSuggestionRequest
  ): Promise<CommitSuggestionResponse> {
    return this.request<CommitSuggestionResponse>(
      `/api/v1/suggestions/${id}/commit`,
      "POST",
      payload || {}
    );
  }
}
