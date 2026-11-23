/**
 * Spindle Obsidian Plugin Main Entry Point.
 * Integrates constraint-driven narrative intelligence into the author's Obsidian workspace.
 */

import { Notice, Plugin, WorkspaceLeaf } from "obsidian";
import { BackendClient } from "./api/backendClient";
import { GenerateModal } from "./modals/generateModal";
import { SuggestionReviewModal } from "./modals/suggestionReviewModal";
import { VaultScanner } from "./services/vaultScanner";
import { DEFAULT_SETTINGS, SpindleSettingTab } from "./settings";
import { SpindleSettings } from "./types";
import { StoryOverviewView, VIEW_TYPE_STORY_OVERVIEW } from "./views/storyOverviewView";

export class SpindlePlugin extends Plugin {
  public settings: SpindleSettings = DEFAULT_SETTINGS;
  public client!: BackendClient;
  public scanner!: VaultScanner;
  private syncDebounceTimer: number | null = null;

  async onload(): Promise<void> {
    await this.loadSettings();

    this.client = new BackendClient(this.settings);
    this.scanner = new VaultScanner(this.app);

    // Register Story Overview side-pane view
    this.registerView(
      VIEW_TYPE_STORY_OVERVIEW,
      (leaf: WorkspaceLeaf) => new StoryOverviewView(leaf, this)
    );

    // Add ribbon icon to toggle Story Overview
    this.addRibbonIcon("book-open", "Spindle Story Overview", () => {
      this.activateView();
    });

    // Register Command: Open Story Overview
    this.addCommand({
      id: "open-story-overview",
      name: "Open Story Overview",
      callback: () => {
        this.activateView();
      },
    });

    // Register Command: Sync Vault to Spindle Backend
    this.addCommand({
      id: "sync-vault",
      name: "Sync Vault to Backend",
      callback: async () => {
        await this.syncVault();
      },
    });

    // Register Command: Generate Narrative Suggestion
    this.addCommand({
      id: "generate-suggestion",
      name: "Generate with AI (Plot Point, Side Story, Continuity)",
      callback: () => {
        new GenerateModal(this.app, this).open();
      },
    });

    // Register Command: Review Generated Suggestions
    this.addCommand({
      id: "review-suggestions",
      name: "Review Suggestions",
      callback: async () => {
        try {
          const suggestions = await this.client.listSuggestions();
          if (suggestions.length === 0) {
            new Notice("No suggestions available for active project.");
            return;
          }
          // Open the most recent pending or latest suggestion
          const pending = suggestions.find(
            (s) => s.approval_status === "pending_author_approval"
          );
          new SuggestionReviewModal(this.app, this, pending || suggestions[0]).open();
        } catch (err: any) {
          new Notice(`Failed to load suggestions: ${err.message}`);
        }
      },
    });

    // Register Settings Tab
    this.addSettingTab(new SpindleSettingTab(this.app, this));

    // Auto-sync listener on file save/modify
    this.registerEvent(
      this.app.vault.on("modify", () => {
        if (this.settings.autoSyncOnSave && this.settings.projectId) {
          this.triggerDebouncedSync();
        }
      })
    );
  }

  async onunload(): Promise<void> {
    if (this.syncDebounceTimer) {
      window.clearTimeout(this.syncDebounceTimer);
    }
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    if (this.client) {
      this.client.updateSettings(this.settings);
    }
  }

  /**
   * Focuses or opens the Spindle Story Overview side-panel view.
   */
  async activateView(): Promise<void> {
    const { workspace } = this.app;
    let leaf: WorkspaceLeaf | null = null;
    const leaves = workspace.getLeavesOfType(VIEW_TYPE_STORY_OVERVIEW);

    if (leaves.length > 0) {
      leaf = leaves[0];
    } else {
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({
          type: VIEW_TYPE_STORY_OVERVIEW,
          active: true,
        });
      }
    }

    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  /**
   * Scans local vault markdown files and synchronizes them with the Spindle backend database.
   */
  async syncVault(): Promise<void> {
    if (!this.settings.projectId) {
      try {
        const overview = await this.client.getStoryOverview();
        if (overview?.project_id) {
          this.settings.projectId = overview.project_id;
          await this.saveSettings();
        }
      } catch {
        new Notice("Cannot sync: No Project ID configured. Open Spindle Settings.");
        return;
      }
    }

    const notice = new Notice("Scanning vault files for Spindle sync...", 8000);

    try {
      const scanResult = await this.scanner.scanVault();
      if (scanResult.files.length === 0) {
        notice.hide();
        new Notice("No markdown files found to sync.");
        return;
      }

      notice.setMessage(
        `Uploading ${scanResult.files.length} vault files to Spindle narrative engine...`
      );

      const syncResult = await this.client.syncVault(scanResult.files);
      notice.hide();

      const indexed = syncResult.indexed_files ?? syncResult.indexed_count ?? 0;
      const total = syncResult.total_files ?? syncResult.total_files_received ?? scanResult.files.length;
      new Notice(
        `✓ Sync Complete! ${indexed}/${total} files indexed.`
      );

      // Refresh any active Story Overview view
      const leaves = this.app.workspace.getLeavesOfType(VIEW_TYPE_STORY_OVERVIEW);
      for (const leaf of leaves) {
        if (leaf.view instanceof StoryOverviewView) {
          await leaf.view.refreshData();
        }
      }
    } catch (err: any) {
      notice.hide();
      new Notice(`Vault sync failed: ${err.message}`);
      console.error("Spindle: Sync failed:", err);
    }
  }

  private triggerDebouncedSync(): void {
    if (this.syncDebounceTimer) {
      window.clearTimeout(this.syncDebounceTimer);
    }
    // Debounce 5 seconds after file modification
    this.syncDebounceTimer = window.setTimeout(async () => {
      await this.syncVault();
    }, 5000);
  }
}

export default SpindlePlugin;
