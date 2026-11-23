/**
 * Narrative Generation Modal for Obsidian.
 * Allows authors to specify generation mode (Plot Point, Side Story, Continuity Analysis),
 * prompt request, timeline position, and involved characters.
 */

import { App, Modal, Notice, Setting } from "obsidian";
import type { SpindlePlugin } from "../main";
import { Suggestion, SuggestionType } from "../types";
import { SuggestionReviewModal } from "./suggestionReviewModal";

export class GenerateModal extends Modal {
  private plugin: SpindlePlugin;
  private mode: SuggestionType = "plot_point";
  private promptText: string = "";
  private narrativePosition: number;
  private charactersInput: string = "";
  private onSuggestionGenerated?: (suggestion: Suggestion) => void;

  constructor(
    app: App,
    plugin: SpindlePlugin,
    onSuggestionGenerated?: (suggestion: Suggestion) => void
  ) {
    super(app);
    this.plugin = plugin;
    this.narrativePosition = plugin.settings.defaultNarrativePosition || 1.0;
    this.onSuggestionGenerated = onSuggestionGenerated;
  }

  onOpen(): void {
    this.modalEl.addClass("spindle-modal-window");
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("spindle-modal-content");

    const header = contentEl.createDiv({ cls: "spindle-modal-header" });
    header.createEl("h2", { text: "Generate with Spindle AI", cls: "spindle-modal-title" });
    contentEl.createEl("p", {
      text: "Request context-grounded, constraint-checked narrative suggestions bounded strictly by your established story canon.",
      cls: "spindle-muted",
    });

    // 1. Generation Mode
    new Setting(contentEl)
      .setName("Generation Mode")
      .setDesc("Select the type of narrative assistance required.")
      .addDropdown((drop) =>
        drop
          .addOption("plot_point", "Plot Point (Scene Continuation)")
          .addOption("side_story", "Side Story (Standalone Vignette)")
          .addOption("continuity_analysis", "Continuity & Consistency Analysis")
          .setValue(this.mode)
          .onChange((val) => {
            this.mode = val as SuggestionType;
          })
      );

    // 2. Request Prompt
    new Setting(contentEl)
      .setName("Author Request / Prompt")
      .setDesc("Describe what should happen, the scene goals, or the continuity question.")
      .addTextArea((ta) => {
        ta.setPlaceholder("e.g. Elena meets with the northern envoys in secret to negotiate passage...")
          .setValue(this.promptText)
          .onChange((val) => {
            this.promptText = val;
          });
        ta.inputEl.rows = 4;
        ta.inputEl.cols = 45;
      });

    // 3. Narrative Position
    new Setting(contentEl)
      .setName("Narrative Timeline Position")
      .setDesc("Position in your story chronology where this takes place (e.g. 1.0 = Beginning, 5.0 = Midpoint, 10.0 = Climax).")
      .addText((t) =>
        t.setValue(String(this.narrativePosition)).onChange((val) => {
          const num = parseFloat(val);
          if (!isNaN(num)) {
            this.narrativePosition = num;
          }
        })
      );

    // 4. Involved Characters
    new Setting(contentEl)
      .setName("Involved Characters")
      .setDesc("Comma-separated character names to involve in this suggestion.")
      .addText((t) =>
        t
          .setPlaceholder("Elena Vareth, Aldric Voss")
          .setValue(this.charactersInput)
          .onChange((val) => {
            this.charactersInput = val;
          })
      );

    // 5. Action Buttons
    const actionsEl = contentEl.createDiv({ cls: "spindle-modal-actions-bar" });
    const cancelBtn = actionsEl.createEl("button", {
      text: "Cancel",
      cls: "spindle-btn-secondary",
    });
    cancelBtn.onClickEvent(() => {
      this.close();
    });

    const generateBtn = actionsEl.createEl("button", {
      text: "✨ Generate Suggestion",
      cls: "spindle-btn-commit is-active",
    });

    generateBtn.onClickEvent(async () => {
      if (!this.promptText.trim()) {
        new Notice("Please enter a prompt request describing what to generate.");
        return;
      }

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

      generateBtn.disabled = true;
      generateBtn.setText("Generating with Multi-Agent Workflow...");
      const notice = new Notice(
        "Spindle agents analyzing canon constraints & generating proposal...",
        10000
      );

      const characters = this.charactersInput
        .split(",")
        .map((c) => c.trim())
        .filter((c) => c.length > 0);

      try {
        let suggestion: Suggestion;
        const payload = {
          request: this.promptText.trim(),
          narrative_position: this.narrativePosition,
          characters: characters.length > 0 ? characters : undefined,
        };

        if (this.mode === "plot_point") {
          suggestion = await this.plugin.client.generatePlotPoint(payload);
        } else if (this.mode === "side_story") {
          suggestion = await this.plugin.client.generateSideStory(payload);
        } else {
          suggestion = await this.plugin.client.generateContinuityAnalysis(payload);
        }

        notice.hide();
        new Notice(`✓ Generated: ${suggestion.title}`);

        this.onSuggestionGenerated?.(suggestion);
        this.close();

        // Immediately open the review modal with the new suggestion
        new SuggestionReviewModal(this.app, this.plugin, suggestion).open();
      } catch (err: any) {
        notice.hide();
        new Notice(`Generation failed: ${err.message}`);
        generateBtn.disabled = false;
        generateBtn.setText("✨ Generate Suggestion");
      }
    });
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
