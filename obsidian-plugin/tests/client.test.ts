import test from "node:test";
import assert from "node:assert/strict";
import { BackendClient } from "../src/api/backendClient";
import { SpindleSettings } from "../src/types";

const mockSettings: SpindleSettings = {
  backendUrl: "http://localhost:8000",
  projectId: "123e4567-e89b-12d3-a456-426614174000",
  defaultDestinationFolder: "Manuscript/Side Stories",
  autoSyncOnSave: false,
  defaultNarrativePosition: 1.0,
};

test("BackendClient - checkHealth sends GET /health", async () => {
  const originalFetch = global.fetch;
  let requestedUrl = "";
  let requestedMethod = "";

  global.fetch = (async (url: any, init: any) => {
    requestedUrl = String(url);
    requestedMethod = init?.method || "GET";
    return {
      ok: true,
      json: async () => ({ status: "ok", environment: "test" }),
    } as any;
  }) as any;

  try {
    const client = new BackendClient(mockSettings);
    const res = await client.checkHealth();
    assert.equal(requestedUrl, "http://localhost:8000/health");
    assert.equal(requestedMethod, "GET");
    assert.equal(res.status, "ok");
  } finally {
    global.fetch = originalFetch;
  }
});

test("BackendClient - syncVault sends POST /api/v1/vault/sync with X-Project-ID header", async () => {
  const originalFetch = global.fetch;
  let requestedUrl = "";
  let requestedHeaders: Record<string, string> = {};
  let requestedBody: any = null;

  global.fetch = (async (url: any, init: any) => {
    requestedUrl = String(url);
    requestedHeaders = init?.headers || {};
    requestedBody = JSON.parse(init?.body || "{}");
    return {
      ok: true,
      json: async () => ({
        status: "success",
        total_files_received: 1,
        indexed_count: 1,
        errors: [],
      }),
    } as any;
  }) as any;

  try {
    const client = new BackendClient(mockSettings);
    const res = await client.syncVault([
      { file_path: "Manuscript/Chapter 1.md", content: "# Chapter 1\nProse here." },
    ]);
    assert.equal(requestedUrl, "http://localhost:8000/api/v1/vault/sync");
    assert.equal(requestedHeaders["X-Project-ID"], mockSettings.projectId);
    assert.equal(requestedBody.files.length, 1);
    assert.equal(res.indexed_count, 1);
  } finally {
    global.fetch = originalFetch;
  }
});

test("BackendClient - getStoryOverview sends GET /api/v1/story/overview", async () => {
  const originalFetch = global.fetch;
  let requestedUrl = "";

  global.fetch = (async (url: any) => {
    requestedUrl = String(url);
    return {
      ok: true,
      json: async () => ({
        project_id: mockSettings.projectId,
        project_name: "Test Universe",
        character_count: 5,
        event_count: 12,
        location_count: 4,
        active_constraints: 3,
        unresolved_threads: 2,
        total_documents: 8,
      }),
    } as any;
  }) as any;

  try {
    const client = new BackendClient(mockSettings);
    const overview = await client.getStoryOverview();
    assert.equal(requestedUrl, "http://localhost:8000/api/v1/story/overview");
    assert.equal(overview.character_count, 5);
    assert.equal(overview.active_constraints, 3);
  } finally {
    global.fetch = originalFetch;
  }
});

test("BackendClient - generate, approve, edit, and commit suggestion requests", async () => {
  const originalFetch = global.fetch;
  const calls: Array<{ url: string; method: string; body: any }> = [];

  global.fetch = (async (url: any, init: any) => {
    calls.push({
      url: String(url),
      method: init?.method || "GET",
      body: init?.body ? JSON.parse(init.body) : undefined,
    });

    if (String(url).endsWith("/approve")) {
      return {
        ok: true,
        json: async () => ({ id: "sug-1", approval_status: "approved" }),
      } as any;
    }
    if (String(url).endsWith("/explore-branches")) {
      return {
        ok: true,
        json: async () => [
          {
            id: "sug-branch-1",
            title: "Confrontation Branch",
            suggestion_type: "plot_point",
            detailed_content: { dramatic_angle: "Confrontation", scene_beats: ["Beat 1"] },
            approval_status: "pending_author_approval",
          },
        ],
      } as any;
    }
    if (String(url).endsWith("/commit")) {
      return {
        ok: true,
        json: async () => ({
          status: "committed",
          file_path: "Manuscript/Side Stories/The Secret.md",
          markdown_content: "# The Secret\nContent",
        }),
      } as any;
    }
    return {
      ok: true,
      json: async () => ({ id: "sug-1", title: "Generated" }),
    } as any;
  }) as any;

  try {
    const client = new BackendClient(mockSettings);

    // 1. Generate Plot Point
    await client.generatePlotPoint({ request: "Elena uncovers a clue.", narrative_position: 2.0 });
    assert.equal(calls[0].url, "http://localhost:8000/api/v1/generate/plot-point");
    assert.equal(calls[0].body.narrative_position, 2.0);

    // 1b. Explore Branches
    const branches = await client.exploreBranches({ narrative_position: 5.0, branch_count: 2 });
    assert.equal(calls[1].url, "http://localhost:8000/api/v1/generate/explore-branches");
    assert.equal(calls[1].body.branch_count, 2);
    assert.equal(branches[0].title, "Confrontation Branch");

    // 2. Approve Suggestion
    const approved = await client.approveSuggestion("sug-1", "Looks great");
    assert.equal(calls[2].url, "http://localhost:8000/api/v1/suggestions/sug-1/approve");
    assert.equal(approved.approval_status, "approved");

    // 3. Commit Suggestion
    const committed = await client.commitSuggestion("sug-1", {
      destination_folder: "Manuscript/Side Stories",
    });
    assert.equal(calls[3].url, "http://localhost:8000/api/v1/suggestions/sug-1/commit");
    assert.equal(committed.file_path, "Manuscript/Side Stories/The Secret.md");
  } finally {
    global.fetch = originalFetch;
  }
});

test("BackendClient - handles HTTP errors with detail parsing", async () => {
  const originalFetch = global.fetch;

  global.fetch = (async () => {
    return {
      ok: false,
      status: 400,
      json: async () => ({ detail: "Invalid lifecycle transition" }),
    } as any;
  }) as any;

  try {
    const client = new BackendClient(mockSettings);
    await assert.rejects(
      async () => client.commitSuggestion("sug-1"),
      /Invalid lifecycle transition/
    );
  } finally {
    global.fetch = originalFetch;
  }
});
