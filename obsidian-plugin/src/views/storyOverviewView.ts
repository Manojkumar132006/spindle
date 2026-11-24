/**
 * Story Overview Side Pane View for Obsidian.
 * Displays live narrative state metrics (characters, events, locations, constraints, unresolved threads)
 * and lists recent suggestions with fast review actions.
 */

import { ItemView, Notice, WorkspaceLeaf } from "obsidian";
import type { SpindlePlugin } from "../main";
import { ExploreBranchesModal } from "../modals/exploreBranchesModal";
import { GenerateModal } from "../modals/generateModal";
import { SuggestionReviewModal } from "../modals/suggestionReviewModal";
import { VaultScaffolder } from "../services/vaultScaffolder";
import { StoryOverview, Suggestion } from "../types";

export const VIEW_TYPE_STORY_OVERVIEW = "spindle-story-overview";

export class StoryOverviewView extends ItemView {
  private plugin: SpindlePlugin;
  private overviewData: StoryOverview | null = null;
  private recentSuggestions: Suggestion[] = [];
  private isLoading: boolean = false;

  constructor(leaf: WorkspaceLeaf, plugin: SpindlePlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE_STORY_OVERVIEW;
  }

  getDisplayText(): string {
    return "Spindle Story Overview";
  }

  getIcon(): string {
    return "book-open";
  }

  async onOpen(): Promise<void> {
    await this.refreshData();
  }

  async refreshData(): Promise<void> {
    if (!this.plugin.settings.projectId) {
      try {
        const defaultOverview = await this.plugin.client.getStoryOverview();
        if (defaultOverview?.project_id) {
          this.plugin.settings.projectId = defaultOverview.project_id;
          await this.plugin.saveSettings();
        }
      } catch {
        this.render();
        return;
      }
    }

    this.isLoading = true;
    this.render();

    try {
      const [overview, suggestions] = await Promise.all([
        this.plugin.client.getStoryOverview(),
        this.plugin.client.listSuggestions(),
      ]);
      this.overviewData = overview;
      this.recentSuggestions = suggestions;
    } catch (err: any) {
      console.error("Spindle: Failed to fetch story overview:", err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  private render(): void {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("spindle-overview-container");

    // Header Bar
    const headerEl = container.createDiv({ cls: "spindle-overview-header" });
    headerEl.createEl("h3", { text: "Narrative Intelligence" });

    const btnRow = headerEl.createDiv({ cls: "spindle-header-buttons" });
    const refreshBtn = btnRow.createEl("button", {
      text: "🔄",
      cls: "spindle-icon-btn",
      title: "Refresh Story State",
    });
    refreshBtn.onClickEvent(async () => {
      await this.refreshData();
      new Notice("Story overview refreshed.");
    });

    if (!this.plugin.settings.projectId) {
      const warnBox = container.createDiv({ cls: "spindle-warning-box" });
      warnBox.createEl("p", {
        text: "No Project ID configured. Open Spindle Settings to set your story Project ID.",
      });
      return;
    }

    if (this.isLoading) {
      const loadingEl = container.createDiv({ cls: "spindle-loading" });
      loadingEl.createEl("p", { text: "Loading narrative state from Spindle..." });
      return;
    }

    // Story Metrics Grid
    if (this.overviewData) {
      const metricsGrid = container.createDiv({ cls: "spindle-metrics-grid" });

      const chars =
        this.overviewData.characters_count ?? this.overviewData.character_count ?? 0;
      const events = this.overviewData.events_count ?? this.overviewData.event_count ?? 0;
      const locs = this.overviewData.locations_count ?? this.overviewData.location_count ?? 0;
      const rules = this.overviewData.world_rules_count ?? 0;
      const constraints =
        this.overviewData.constraints_count ?? this.overviewData.active_constraints ?? 0;
      const threads =
        this.overviewData.open_threads_count ?? this.overviewData.unresolved_threads ?? 0;
      const docs = this.overviewData.documents_count ?? this.overviewData.total_documents ?? 0;

      this.createMetricCard(metricsGrid, "🎭 Characters", chars);
      this.createMetricCard(metricsGrid, "⏳ Events", events);
      this.createMetricCard(metricsGrid, "🏰 Locations", locs);
      this.createMetricCard(metricsGrid, "📜 World Rules", rules);
      this.createMetricCard(metricsGrid, "⚠️ Constraints", constraints);
      this.createMetricCard(metricsGrid, "❓ Open Threads", threads);
      this.createMetricCard(metricsGrid, "📄 Documents", docs);
    }

    // Action Buttons
    const actionsBar = container.createDiv({ cls: "spindle-overview-actions" });
    const exploreBtn = actionsBar.createEl("button", {
      text: "🌿 Explore Branches",
      cls: "mod-cta spindle-action-btn",
      title: "Discover divergent story pathways without writing a prompt",
    });
    exploreBtn.onClickEvent(() => {
      new ExploreBranchesModal(this.app, this.plugin, () => this.refreshData()).open();
    });

    const generateBtn = actionsBar.createEl("button", {
      text: "✨ Generate with AI",
      cls: "spindle-action-btn",
    });
    generateBtn.onClickEvent(() => {
      new GenerateModal(this.app, this.plugin, () => this.refreshData()).open();
    });

    const syncBtn = actionsBar.createEl("button", {
      text: "🔄 Sync Vault",
      cls: "spindle-action-btn",
    });
    syncBtn.onClickEvent(async () => {
      syncBtn.disabled = true;
      syncBtn.setText("Syncing...");
      try {
        await this.plugin.syncVault();
        await this.refreshData();
      } finally {
        syncBtn.disabled = false;
        syncBtn.setText("🔄 Sync Vault");
      }
    });

    const scaffoldBtn = actionsBar.createEl("button", {
      text: "📁 Scaffold Vault",
      cls: "spindle-action-btn",
      title: "Create standard novel writing folders and templates",
    });
    scaffoldBtn.onClickEvent(async () => {
      scaffoldBtn.disabled = true;
      scaffoldBtn.setText("Scaffolding...");
      try {
        const scaffolder = new VaultScaffolder(this.app);
        const res = await scaffolder.scaffoldAll();
        new Notice(
          `Scaffolded: ${res.foldersCreated.length} folders, ${res.filesCreated.length} templates & docs, ${res.configsUpdated.length} configs.`
        );
        await this.refreshData();
      } catch (err: any) {
        new Notice(`Scaffolding failed: ${err.message}`);
      } finally {
        scaffoldBtn.disabled = false;
        scaffoldBtn.setText("📁 Scaffold Vault");
      }
    });

    // Recent Suggestions Section
    const sugSection = container.createDiv({ cls: "spindle-suggestions-section" });
    sugSection.createEl("h4", { text: "Recent Suggestions" });

    if (this.recentSuggestions.length === 0) {
      sugSection.createEl("p", {
        text: "No suggestions generated yet. Click 'Generate with AI' to begin.",
        cls: "spindle-muted",
      });
    } else {
      const listEl = sugSection.createDiv({ cls: "spindle-suggestion-cards" });
      this.recentSuggestions.slice(0, 10).forEach((sug) => {
        const card = listEl.createDiv({ cls: "spindle-suggestion-card" });
        const titleRow = card.createDiv({ cls: "spindle-card-title-row" });
        titleRow.createEl("strong", { text: sug.title || "Untitled" });

        const statusPill = titleRow.createSpan({
          cls: `spindle-badge status-${sug.approval_status}`,
          text: sug.approval_status.replace(/_/g, " "),
        });

        if (sug.premise) {
          card.createEl("p", {
            text: sug.premise.length > 90 ? sug.premise.substring(0, 90) + "..." : sug.premise,
            cls: "spindle-card-premise",
          });
        }

        card.onClickEvent(() => {
          new SuggestionReviewModal(this.app, this.plugin, sug, () => {
            this.refreshData();
          }).open();
        });
      });
    }
  }

  private createMetricCard(container: HTMLElement, label: string, value: number): void {
    const card = container.createDiv({ cls: "spindle-metric-card" });
    card.createEl("span", { text: label, cls: "spindle-metric-label" });
    card.createEl("strong", { text: String(value ?? 0), cls: "spindle-metric-value" });
  }
}
