/**
 * Suggestion Review & Canon Commitment Modal for Obsidian.
 * Allows authors to review generated suggestions, inspect constraint validation reports,
 * edit or reject proposals, and safely commit approved content into the vault as native Markdown.
 */

import { App, Modal, Notice, Setting, TFile } from "obsidian";
import type { SpindlePlugin } from "../main";
import { Suggestion, ValidationReport, ValidatorResult } from "../types";

export class SuggestionReviewModal extends Modal {
  private plugin: SpindlePlugin;
  private suggestion: Suggestion;
  private isEditing: boolean = false;
  private onStatusChange?: (updated: Suggestion) => void;

  constructor(
    app: App,
    plugin: SpindlePlugin,
    suggestion: Suggestion,
    onStatusChange?: (updated: Suggestion) => void
  ) {
    super(app);
    this.plugin = plugin;
    this.suggestion = suggestion;
    this.onStatusChange = onStatusChange;
  }

  onOpen(): void {
    this.render();
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }

  private render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("spindle-suggestion-modal");

    // Modal Title Bar
    const headerEl = contentEl.createDiv({ cls: "spindle-modal-header" });
    headerEl.createEl("h2", { text: this.suggestion.title || "Narrative Suggestion" });

    const badgesEl = headerEl.createDiv({ cls: "spindle-badge-group" });
    const typeBadge = badgesEl.createSpan({
      cls: "spindle-badge spindle-badge-type",
      text: this.suggestion.suggestion_type.replace(/_/g, " ").toUpperCase(),
    });

    const statusBadge = badgesEl.createSpan({
      cls: `spindle-badge spindle-badge-status status-${this.suggestion.approval_status}`,
      text: this.suggestion.approval_status.replace(/_/g, " ").toUpperCase(),
    });

    if (this.isEditing) {
      this.renderEditForm(contentEl);
    } else {
      this.renderViewForm(contentEl);
    }
  }

  private renderViewForm(containerEl: HTMLElement): void {
    // 1. Premise Section
    const premiseSec = containerEl.createDiv({ cls: "spindle-section" });
    premiseSec.createEl("h4", { text: "Premise" });
    premiseSec.createEl("p", {
      text: this.suggestion.premise || "No premise provided.",
      cls: "spindle-premise-text",
    });

    // 2. Outline & Beats
    const beatsSec = containerEl.createDiv({ cls: "spindle-section" });
    beatsSec.createEl("h4", { text: "Scene Beats & Outline" });
    const beats =
      this.suggestion.detailed_content?.scene_beats ||
      this.suggestion.detailed_content?.beats ||
      (this.suggestion.detailed_content?.beat ? [this.suggestion.detailed_content.beat] : []);

    if (beats && beats.length > 0) {
      const beatList = beatsSec.createEl("ol", { cls: "spindle-beat-list" });
      beats.forEach((beat: string) => {
        beatList.createEl("li", { text: beat });
      });
    } else {
      beatsSec.createEl("p", { text: "No individual beats detailed.", cls: "spindle-muted" });
    }

    // 3. Supporting Evidence & Canon Sources
    if (this.suggestion.supporting_evidence && this.suggestion.supporting_evidence.length > 0) {
      const evidenceSec = containerEl.createDiv({ cls: "spindle-section" });
      evidenceSec.createEl("h4", { text: "Supporting Evidence & Sources" });
      const evList = evidenceSec.createEl("ul", { cls: "spindle-evidence-list" });
      this.suggestion.supporting_evidence.forEach((src) => {
        const item = evList.createEl("li");
        const linkText = src.startsWith("[[") ? src : `[[${src}]]`;
        item.createEl("span", { text: linkText, cls: "spindle-wikilink" });
      });
    }

    // 4. Assumptions
    if (this.suggestion.assumptions && this.suggestion.assumptions.length > 0) {
      const assumpSec = containerEl.createDiv({ cls: "spindle-section" });
      assumpSec.createEl("h4", { text: "Narrative Assumptions" });
      const assumpList = assumpSec.createEl("ul");
      this.suggestion.assumptions.forEach((a) => {
        assumpList.createEl("li", { text: a });
      });
    }

    // 5. Constraint Validation Inspector
    this.renderValidationReport(containerEl);

    // 6. Action Buttons Bar
    this.renderActionButtons(containerEl);
  }

  private renderValidationReport(containerEl: HTMLElement): void {
    const reportSec = containerEl.createDiv({ cls: "spindle-section spindle-validation-report" });
    reportSec.createEl("h4", { text: "Constraint Validation Report" });

    const val = this.suggestion.validation_results;
    if (!val) {
      reportSec.createEl("p", { text: "No validation results recorded.", cls: "spindle-muted" });
      return;
    }

    const outcome = val.overall_outcome || (val.has_hard_failures ? "FAIL" : "PASS");
    const banner = reportSec.createDiv({
      cls: `spindle-validation-banner banner-${outcome.toLowerCase()}`,
    });
    banner.createSpan({
      text: `Outcome: ${outcome} ${outcome === "PASS" ? "✓" : outcome === "WARNING" ? "⚠️" : "✗"}`,
    });

    const validatorResults: ValidatorResult[] =
      val.validator_results || val.results || [];

    if (validatorResults.length > 0) {
      const resultsContainer = reportSec.createDiv({ cls: "spindle-validator-results" });
      validatorResults.forEach((vr) => {
        const item = resultsContainer.createDiv({ cls: "spindle-validator-item" });
        const topRow = item.createDiv({ cls: "spindle-validator-top" });
        topRow.createSpan({ text: vr.validator_name, cls: "spindle-validator-name" });
        topRow.createSpan({
          text: vr.outcome,
          cls: `spindle-badge outcome-${vr.outcome.toLowerCase()}`,
        });

        if (vr.issues && vr.issues.length > 0) {
          const issueList = item.createEl("ul", { cls: "spindle-issue-list" });
          vr.issues.forEach((issue) => {
            const li = issueList.createEl("li");
            li.createSpan({
              text: `[${issue.severity.toUpperCase()}] `,
              cls: `severity-tag severity-${issue.severity.toLowerCase()}`,
            });
            li.createSpan({ text: issue.message });
          });
        }
      });
    }
  }

  private renderActionButtons(containerEl: HTMLElement): void {
    const actionsBar = containerEl.createDiv({ cls: "spindle-modal-actions" });

    // Approve Button
    if (
      this.suggestion.approval_status === "pending_author_approval" ||
      this.suggestion.approval_status === "validated"
    ) {
      const approveBtn = actionsBar.createEl("button", {
        text: "Approve Suggestion",
        cls: "mod-cta spindle-action-btn",
      });
      approveBtn.onClickEvent(async () => {
        approveBtn.disabled = true;
        try {
          const updated = await this.plugin.client.approveSuggestion(this.suggestion.id);
          this.suggestion = updated;
          this.onStatusChange?.(updated);
          new Notice(`Approved: ${updated.title}`);
          this.render();
        } catch (err: any) {
          new Notice(`Failed to approve: ${err.message}`);
          approveBtn.disabled = false;
        }
      });
    }

    // Edit Button
    if (this.suggestion.approval_status !== "committed") {
      const editBtn = actionsBar.createEl("button", {
        text: "Edit Suggestion",
        cls: "spindle-action-btn",
      });
      editBtn.onClickEvent(() => {
        this.isEditing = true;
        this.render();
      });
    }

    // Reject Button
    if (
      this.suggestion.approval_status !== "committed" &&
      this.suggestion.approval_status !== "rejected"
    ) {
      const rejectBtn = actionsBar.createEl("button", {
        text: "Reject",
        cls: "mod-warning spindle-action-btn",
      });
      rejectBtn.onClickEvent(async () => {
        const reason = prompt("Please provide a reason for rejecting this suggestion:");
        if (!reason || reason.trim().length < 3) {
          new Notice("Rejection cancelled: A valid reason (min 3 characters) is required.");
          return;
        }

        rejectBtn.disabled = true;
        try {
          const updated = await this.plugin.client.rejectSuggestion(
            this.suggestion.id,
            reason.trim()
          );
          this.suggestion = updated;
          this.onStatusChange?.(updated);
          new Notice(`Rejected: ${updated.title}`);
          this.render();
        } catch (err: any) {
          new Notice(`Failed to reject: ${err.message}`);
          rejectBtn.disabled = false;
        }
      });
    }

    // Commit to Vault Button (Only enabled when APPROVED or EDITED)
    const canCommit =
      this.suggestion.approval_status === "approved" ||
      this.suggestion.approval_status === "edited";

    const commitBtn = actionsBar.createEl("button", {
      text: "Commit to Vault Canon",
      cls: `spindle-commit-btn ${canCommit ? "mod-cta" : "is-disabled"}`,
    });
    commitBtn.disabled = !canCommit;

    commitBtn.onClickEvent(async () => {
      if (!canCommit) {
        new Notice("Suggestion must be Approved or Edited before committing to canon.");
        return;
      }

      commitBtn.disabled = true;
      commitBtn.setText("Committing...");

      try {
        const folder = this.plugin.settings.defaultDestinationFolder || "Manuscript/Side Stories";
        const commitResult = await this.plugin.client.commitSuggestion(this.suggestion.id, {
          destination_folder: folder,
        });

        // Write note safely into Obsidian vault
        await this.writeToVault(commitResult.file_path, commitResult.markdown_content);

        new Notice(`Committed "${this.suggestion.title}" to ${commitResult.file_path}!`);
        this.suggestion.approval_status = "committed";
        this.onStatusChange?.(this.suggestion);
        this.close();
      } catch (err: any) {
        new Notice(`Commit failed: ${err.message}`);
        commitBtn.disabled = false;
        commitBtn.setText("Commit to Vault Canon");
      }
    });
  }

  private renderEditForm(containerEl: HTMLElement): void {
    const editContainer = containerEl.createDiv({ cls: "spindle-edit-container" });
    editContainer.createEl("h3", { text: "Edit Suggestion" });

    let titleVal = this.suggestion.title;
    let premiseVal = this.suggestion.premise;
    const existingBeats =
      this.suggestion.detailed_content?.scene_beats ||
      this.suggestion.detailed_content?.beats ||
      (this.suggestion.detailed_content?.beat ? [this.suggestion.detailed_content.beat] : []);
    let beatsTextVal = existingBeats.join("\n");
    let editSummaryVal = "Author refined prose and beats";

    new Setting(editContainer).setName("Title").addText((t) =>
      t.setValue(titleVal).onChange((v) => {
        titleVal = v;
      })
    );

    new Setting(editContainer).setName("Premise").addTextArea((ta) => {
      ta.setValue(premiseVal).onChange((v) => {
        premiseVal = v;
      });
      ta.inputEl.rows = 4;
      ta.inputEl.cols = 40;
    });

    new Setting(editContainer)
      .setName("Scene Beats (one per line)")
      .addTextArea((ta) => {
        ta.setValue(beatsTextVal).onChange((v) => {
          beatsTextVal = v;
        });
        ta.inputEl.rows = 6;
        ta.inputEl.cols = 40;
      });

    new Setting(editContainer).setName("Edit Summary / Notes").addText((t) =>
      t.setValue(editSummaryVal).onChange((v) => {
        editSummaryVal = v;
      })
    );

    const btnRow = editContainer.createDiv({ cls: "spindle-modal-actions" });
    const saveBtn = btnRow.createEl("button", {
      text: "Save & Validate Edits",
      cls: "mod-cta spindle-action-btn",
    });
    saveBtn.onClickEvent(async () => {
      saveBtn.disabled = true;
      try {
        const parsedBeats = beatsTextVal
          .split("\n")
          .map((b) => b.trim())
          .filter((b) => b.length > 0);

        const updated = await this.plugin.client.editSuggestion(this.suggestion.id, {
          title: titleVal,
          premise: premiseVal,
          detailed_content: {
            ...this.suggestion.detailed_content,
            scene_beats: parsedBeats,
          },
          edit_summary: editSummaryVal,
        });

        this.suggestion = updated;
        this.isEditing = false;
        this.onStatusChange?.(updated);
        new Notice("Edits saved and suggestion updated.");
        this.render();
      } catch (err: any) {
        new Notice(`Failed to save edits: ${err.message}`);
        saveBtn.disabled = false;
      }
    });

    const cancelBtn = btnRow.createEl("button", { text: "Cancel", cls: "spindle-action-btn" });
    cancelBtn.onClickEvent(() => {
      this.isEditing = false;
      this.render();
    });
  }

  /**
   * Safely writes committed content into the local vault, creating parent directories as necessary.
   */
  private async writeToVault(filePath: string, content: string): Promise<void> {
    const normalized = filePath.replace(/\\/g, "/");
    const parts = normalized.split("/");
    const fileName = parts.pop()!;
    const folderPath = parts.join("/");

    if (folderPath) {
      await this.ensureFolderExists(folderPath);
    }

    const existingFile = this.app.vault.getAbstractFileByPath(normalized);
    if (existingFile instanceof TFile) {
      await this.app.vault.modify(existingFile, content);
      await this.app.workspace.openLinkText(normalized, "", false);
    } else {
      const createdFile = await this.app.vault.create(normalized, content);
      await this.app.workspace.openLinkText(createdFile.path, "", false);
    }
  }

  private async ensureFolderExists(folderPath: string): Promise<void> {
    const folders = folderPath.split("/");
    let current = "";
    for (const f of folders) {
      current = current ? `${current}/${f}` : f;
      const exists = this.app.vault.getAbstractFileByPath(current);
      if (!exists) {
        await this.app.vault.createFolder(current);
      }
    }
  }
}
