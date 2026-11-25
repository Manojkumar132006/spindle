/**
 * Explore Narrative Branches Modal for Obsidian.
 * Allows authors to discover multiple divergent narrative pathways
 * without entering prompts. Each branch is constraint-validated by Spindle.
 */

import { App, Modal, Notice, Setting } from "obsidian";
import type { SpindlePlugin } from "../main";
import { Suggestion } from "../types";
import { SuggestionReviewModal } from "./suggestionReviewModal";

export class ExploreBranchesModal extends Modal {
  private plugin: SpindlePlugin;
  private narrativePosition: number;
  private branchCount: number = 3;
  private targetCharactersInput: string = "";
  private onBranchSelected?: (suggestion: Suggestion) => void;
  private branches: Suggestion[] = [];
  private isLoading: boolean = false;

  constructor(
    app: App,
    plugin: SpindlePlugin,
    onBranchSelected?: (suggestion: Suggestion) => void
  ) {
    super(app);
    this.plugin = plugin;
    this.narrativePosition = plugin.settings.defaultNarrativePosition || 1.0;
    this.onBranchSelected = onBranchSelected;
  }

  onOpen(): void {
    this.modalEl.addClass("spindle-modal-window");
    this.render();
  }

  private render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("spindle-modal-content");

    const header = contentEl.createDiv({ cls: "spindle-modal-header" });
    header.createEl("h2", { text: "🌿 Explore Narrative Branches", cls: "spindle-modal-title" });
    contentEl.createEl("p", {
      text: "Synthesize divergent narrative pathways from your current story position without writing prompts. Each branch is checked against established canon constraints.",
      cls: "spindle-muted",
    });

    if (this.branches.length === 0 && !this.isLoading) {
      this.renderSetupForm(contentEl);
    } else if (this.isLoading) {
      this.renderLoading(contentEl);
    } else {
      this.renderBranchOptions(contentEl);
    }
  }

  private renderSetupForm(container: HTMLElement): void {
    const formBox = container.createDiv({ cls: "spindle-form-container" });

    // 1. Narrative Position
    new Setting(formBox)
      .setName("Story Timeline Position")
      .setDesc("The chronological story point from which branches diverge (e.g. 1.0 = Beginning, 5.0 = Midpoint, 10.0 = Climax).")
      .addText((t) =>
        t.setValue(String(this.narrativePosition)).onChange((val) => {
          const num = parseFloat(val);
          if (!isNaN(num)) {
            this.narrativePosition = num;
          }
        })
      );

    // 2. Branch Count
    new Setting(formBox)
      .setName("Number of Divergent Pathways")
      .setDesc("How many distinct narrative angles to synthesize (2 to 5 branches).")
      .addDropdown((d) =>
        d
          .addOption("2", "2 Pathways (Focused)")
          .addOption("3", "3 Pathways (Standard)")
          .addOption("4", "4 Pathways (Broad)")
          .addOption("5", "5 Pathways (Comprehensive)")
          .setValue(String(this.branchCount))
          .onChange((val) => {
            this.branchCount = parseInt(val, 10);
          })
      );

    // 3. Target Characters (Optional)
    new Setting(formBox)
      .setName("Focus Characters (Optional)")
      .setDesc("Comma-separated names of characters to center these branches around. Leave empty to auto-select key characters.")
      .addText((t) =>
        t
          .setPlaceholder("e.g. Elena Vareth, Aldric Voss")
          .setValue(this.targetCharactersInput)
          .onChange((val) => {
            this.targetCharactersInput = val;
          })
      );

    // Action Buttons
    const actionsEl = container.createDiv({ cls: "spindle-modal-actions-bar" });
    const cancelBtn = actionsEl.createEl("button", {
      text: "Cancel",
      cls: "spindle-btn-secondary",
    });
    cancelBtn.onClickEvent(() => {
      this.close();
    });

    const exploreBtn = actionsEl.createEl("button", {
      text: "🔍 Explore Divergent Branches",
      cls: "spindle-btn-commit is-active",
    });

    exploreBtn.onClickEvent(async () => {
      await this.runBranchExploration();
    });
  }

  private renderLoading(container: HTMLElement): void {
    const loadingBox = container.createDiv({ cls: "spindle-loading-pane" });
    loadingBox.createEl("div", { cls: "spindle-spinner" });
    loadingBox.createEl("h3", { text: "Synthesizing Divergent Pathways..." });
    loadingBox.createEl("p", {
      text: "Story Architect and Constraint Engine agents are evaluating character motivations, causal dependencies, and canon rules...",
      cls: "spindle-muted",
    });
  }

  private renderBranchOptions(container: HTMLElement): void {
    const topBar = container.createDiv({ cls: "spindle-branches-topbar" });
    topBar.createEl("span", {
      text: `Discovered ${this.branches.length} Divergent Pathways at Position ${this.narrativePosition}:`,
      cls: "spindle-subhead",
    });

    const reexploreBtn = topBar.createEl("button", {
      text: "🔄 Adjust & Re-run",
      cls: "spindle-btn-secondary spindle-btn-small",
    });
    reexploreBtn.onClickEvent(() => {
      this.branches = [];
      this.render();
    });

    const grid = container.createDiv({ cls: "spindle-branch-grid" });

    this.branches.forEach((branch, idx) => {
      const card = grid.createDiv({ cls: "spindle-branch-card" });

      // Title & Angle
      const headerRow = card.createDiv({ cls: "spindle-branch-header-row" });
      headerRow.createEl("h3", { text: `${idx + 1}. ${branch.title}`, cls: "spindle-branch-title" });

      const angle =
        branch.detailed_content?.dramatic_angle ||
        branch.detailed_content?.angle ||
        "NARRATIVE TRAJECTORY";
      headerRow.createSpan({
        text: angle.toUpperCase(),
        cls: "spindle-badge spindle-badge-angle",
      });

      // Premise
      if (branch.premise) {
        card.createEl("p", { text: branch.premise, cls: "spindle-branch-premise" });
      }

      // Key Beats
      const beats = branch.detailed_content?.scene_beats || branch.detailed_content?.beats || [];
      if (beats.length > 0) {
        card.createEl("strong", { text: "Key Narrative Beats:", cls: "spindle-branch-section-label" });
        const beatList = card.createEl("ol", { cls: "spindle-branch-beats-list" });
        beats.slice(0, 3).forEach((beat: string) => {
          beatList.createEl("li", { text: beat });
        });
      }

      // Characters & Evidence
      const chars = branch.detailed_content?.involved_characters || [];
      if (chars.length > 0) {
        const charRow = card.createDiv({ cls: "spindle-branch-meta-row" });
        charRow.createEl("span", { text: "Cast: ", cls: "spindle-muted-label" });
        const charPills = charRow.createDiv({ cls: "spindle-char-pills" });
        chars.forEach((c: string) => {
          charPills.createSpan({ text: c, cls: "spindle-char-pill" });
        });
      }

      // Validation status
      const valReport = branch.validation_results;
      const valOutcome = valReport?.overall_outcome || "PASS";
      const valRow = card.createDiv({ cls: "spindle-branch-val-row" });
      valRow.createSpan({
        text: valOutcome === "PASS" ? "✓ Canon Validated" : `⚠ ${valOutcome}`,
        cls: `spindle-mini-pill pill-${valOutcome.toLowerCase()}`,
      });

      if (branch.detailed_content?.causal_consequences?.length) {
        const fallout = Array.isArray(branch.detailed_content.causal_consequences)
          ? branch.detailed_content.causal_consequences[0]
          : branch.detailed_content.causal_consequences;
        valRow.createSpan({
          text: `Stakes: ${fallout}`,
          cls: "spindle-branch-stakes",
        });
      }

      // Card action button
      const actionRow = card.createDiv({ cls: "spindle-branch-action-row" });
      const selectBtn = actionRow.createEl("button", {
        text: "Review & Commit Branch ➔",
        cls: "spindle-btn-commit",
      });

      selectBtn.onClickEvent(() => {
        this.close();
        if (this.onBranchSelected) {
          this.onBranchSelected(branch);
        }
        new SuggestionReviewModal(this.app, this.plugin, branch, () => {
          if (this.onBranchSelected) {
            this.onBranchSelected(branch);
          }
        }).open();
      });
    });
  }

  private async runBranchExploration(): Promise<void> {
    if (!this.plugin.settings.projectId) {
      try {
        const overview = await this.plugin.client.getStoryOverview();
        if (overview?.project_id) {
          this.plugin.settings.projectId = overview.project_id;
          await this.plugin.saveSettings();
        }
      } catch {
        new Notice("No Project ID configured. Please set your Project ID in Spindle Settings.");
        return;
      }
    }

    this.isLoading = true;
    this.render();

    const characters = this.targetCharactersInput
      .split(",")
      .map((c) => c.trim())
      .filter((c) => c.length > 0);

    const notice = new Notice(
      "Synthesizing divergent narrative branches with constraint validation...",
      15000
    );

    try {
      const branches = await this.plugin.client.exploreBranches({
        narrative_position: this.narrativePosition,
        branch_count: this.branchCount,
        target_characters: characters.length > 0 ? characters : undefined,
      });

      notice.hide();

      if (!branches || branches.length === 0) {
        new Notice("No narrative branches returned for this position.");
        this.isLoading = false;
        this.render();
        return;
      }

      this.branches = branches;
      this.isLoading = false;
      this.render();
      new Notice(`Explored ${branches.length} divergent pathways!`);
    } catch (err: any) {
      notice.hide();
      this.isLoading = false;
      this.render();
      new Notice(`Branch exploration failed: ${err.message}`, 6000);
    }
  }
}
