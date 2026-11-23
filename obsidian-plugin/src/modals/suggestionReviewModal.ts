/**
 * Suggestion Review & Canon Commitment Modal for Obsidian.
 * Allows authors to review generated suggestions, inspect constraint validation reports,
 * edit or reject proposals, and safely commit approved content into the vault as native Markdown.
 */

import { App, Modal, Notice, Setting, TFile } from "obsidian";
import type { SpindlePlugin } from "../main";
import {
  DiagnosticItem,
  Suggestion,
  ValidationReport,
  ValidatorResult,
} from "../types";

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
    this.modalEl.addClass("spindle-modal-window");
    this.render();
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }

  private render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("spindle-modal-content");

    // Modal Title Bar
    const headerEl = contentEl.createDiv({ cls: "spindle-modal-header" });
    const titleGroup = headerEl.createDiv({ cls: "spindle-header-title-group" });
    titleGroup.createEl("h2", {
      text: this.suggestion.title || "Narrative Suggestion",
      cls: "spindle-modal-title",
    });

    const badgesEl = headerEl.createDiv({ cls: "spindle-badge-group" });
    badgesEl.createSpan({
      cls: "spindle-badge spindle-badge-type",
      text: this.suggestion.suggestion_type.replace(/_/g, " ").toUpperCase(),
    });

    badgesEl.createSpan({
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
    const bodyEl = containerEl.createDiv({ cls: "spindle-modal-body" });

    // 1. Premise Section Card
    const premiseCard = bodyEl.createDiv({ cls: "spindle-card spindle-premise-card" });
    premiseCard.createEl("span", { text: "💡 PREMISE", cls: "spindle-card-tag" });
    premiseCard.createEl("p", {
      text: this.suggestion.premise || "No premise provided.",
      cls: "spindle-premise-text",
    });

    // 2. Outline & Beats Card
    const beats =
      this.suggestion.detailed_content?.scene_beats ||
      this.suggestion.detailed_content?.beats ||
      (this.suggestion.detailed_content?.beat ? [this.suggestion.detailed_content.beat] : []);

    if (beats && beats.length > 0) {
      const beatsCard = bodyEl.createDiv({ cls: "spindle-card spindle-beats-card" });
      beatsCard.createEl("span", { text: "🎬 SCENE BEATS & OUTLINE", cls: "spindle-card-tag" });
      const beatList = beatsCard.createEl("ol", { cls: "spindle-beat-list" });
      beats.forEach((beat: string) => {
        beatList.createEl("li", { text: beat });
      });
    }

    // 3. Supporting Evidence & Canon Sources Card
    if (this.suggestion.supporting_evidence && this.suggestion.supporting_evidence.length > 0) {
      const evidenceCard = bodyEl.createDiv({ cls: "spindle-card spindle-evidence-card" });
      evidenceCard.createEl("span", {
        text: "🔗 CANON EVIDENCE & SOURCES",
        cls: "spindle-card-tag",
      });
      const evList = evidenceCard.createDiv({ cls: "spindle-evidence-pills" });
      this.suggestion.supporting_evidence.forEach((src) => {
        const linkText = src.startsWith("[[") ? src : `[[${src}]]`;
        evList.createSpan({ text: linkText, cls: "spindle-wikilink-pill" });
      });
    }

    // 4. Assumptions Card
    if (this.suggestion.assumptions && this.suggestion.assumptions.length > 0) {
      const assumpCard = bodyEl.createDiv({ cls: "spindle-card spindle-assump-card" });
      assumpCard.createEl("span", { text: "💭 ASSUMPTIONS", cls: "spindle-card-tag" });
      const assumpList = assumpCard.createEl("ul", { cls: "spindle-clean-list" });
      this.suggestion.assumptions.forEach((a) => {
        assumpList.createEl("li", { text: a });
      });
    }

    // 5. Constraint Validation Inspector
    this.renderValidationReport(bodyEl);

    // 6. Action Buttons Bar
    this.renderActionButtons(containerEl);
  }

  private renderValidationReport(containerEl: HTMLElement): void {
    const reportCard = containerEl.createDiv({ cls: "spindle-card spindle-validation-card" });
    reportCard.createEl("span", {
      text: "🛡️ CONSTRAINT VALIDATION REPORT",
      cls: "spindle-card-tag",
    });

    const val = this.suggestion.validation_results;
    if (!val) {
      reportCard.createEl("p", {
        text: "No validation results recorded.",
        cls: "spindle-muted",
      });
      return;
    }

    const outcome = val.overall_outcome || (val.has_hard_failures ? "FAIL" : "PASS");
    const isPass = outcome.toUpperCase() === "PASS";
    const isWarning = outcome.toUpperCase() === "WARNING";

    // Summary Banner
    const banner = reportCard.createDiv({
      cls: `spindle-validation-banner banner-${outcome.toLowerCase()}`,
    });

    const bannerHeader = banner.createDiv({ cls: "spindle-banner-header" });
    bannerHeader.createSpan({
      text: isPass ? "✓ All Constraints Satisfied" : isWarning ? "⚠️ Validation Warnings Detected" : "✗ Hard Constraint Violations Detected",
      cls: "spindle-banner-title",
    });

    // Summary stats strip
    const statsStrip = banner.createDiv({ cls: "spindle-banner-stats" });
    if (val.passed_count !== undefined) {
      statsStrip.createSpan({
        text: `${val.passed_count} Passed`,
        cls: "spindle-mini-pill pill-pass",
      });
    }
    if (val.warning_count !== undefined && val.warning_count > 0) {
      statsStrip.createSpan({
        text: `${val.warning_count} Warnings`,
        cls: "spindle-mini-pill pill-warn",
      });
    }
    if (val.failed_count !== undefined && val.failed_count > 0) {
      statsStrip.createSpan({
        text: `${val.failed_count} Failed`,
        cls: "spindle-mini-pill pill-fail",
      });
    }

    if (val.summary) {
      banner.createEl("p", { text: val.summary, cls: "spindle-banner-desc" });
    }

    // Diagnostics / Validator details list
    const diagnostics: Array<any> =
      val.diagnostics || val.validator_results || val.results || [];

    if (diagnostics.length > 0) {
      const itemsContainer = reportCard.createDiv({ cls: "spindle-diagnostics-container" });

      diagnostics.forEach((diag) => {
        const itemOutcome = (diag.outcome || "PASS").toUpperCase();
        const ruleName = diag.rule_name || diag.validator_name || diag.rule_id || "Constraint";
        const itemCard = itemsContainer.createDiv({
          cls: `spindle-diagnostic-item diag-outcome-${itemOutcome.toLowerCase()}`,
        });

        const topRow = itemCard.createDiv({ cls: "spindle-diag-top" });
        topRow.createSpan({ text: ruleName, cls: "spindle-diag-title" });
        topRow.createSpan({
          text: itemOutcome,
          cls: `spindle-badge outcome-${itemOutcome.toLowerCase()}`,
        });

        // Message
        if (diag.message) {
          itemCard.createEl("p", { text: diag.message, cls: "spindle-diag-message" });
        }

        // Issues list if structured like validator_results
        if (diag.issues && diag.issues.length > 0) {
          const issueList = itemCard.createEl("ul", { cls: "spindle-diag-issues" });
          diag.issues.forEach((issue: any) => {
            const li = issueList.createEl("li");
            li.createSpan({
              text: `[${(issue.severity || "warning").toUpperCase()}] `,
              cls: `severity-tag severity-${(issue.severity || "").toLowerCase()}`,
            });
            li.createSpan({ text: issue.message || issue.rule_type });
          });
        }

        // Evidence
        if (diag.evidence && diag.evidence.length > 0) {
          const evContainer = itemCard.createDiv({ cls: "spindle-diag-evidence" });
          evContainer.createSpan({ text: "Evidence: ", cls: "spindle-evidence-label" });
          diag.evidence.forEach((ev: string) => {
            evContainer.createSpan({ text: ev, cls: "spindle-evidence-tag" });
          });
        }

        // Remediation Hint / Recommendation
        if (diag.remediation_hint) {
          const hintBox = itemCard.createDiv({ cls: "spindle-remediation-box" });
          hintBox.createSpan({ text: "💡 Recommendation: ", cls: "spindle-hint-label" });
          hintBox.createSpan({ text: diag.remediation_hint });
        }
      });
    }
  }

  private renderActionButtons(containerEl: HTMLElement): void {
    const actionsBar = containerEl.createDiv({ cls: "spindle-modal-actions-bar" });

    // Left: Close button
    const leftActions = actionsBar.createDiv({ cls: "spindle-actions-left" });
    const closeBtn = leftActions.createEl("button", {
      text: "Close",
      cls: "spindle-btn-secondary",
    });
    closeBtn.onClickEvent(() => this.close());

    // Right: Action buttons
    const rightActions = actionsBar.createDiv({ cls: "spindle-actions-right" });

    // Reject Button
    if (
      this.suggestion.approval_status !== "committed" &&
      this.suggestion.approval_status !== "rejected"
    ) {
      const rejectBtn = rightActions.createEl("button", {
        text: "Reject",
        cls: "spindle-btn-danger",
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

    // Edit Button
    if (this.suggestion.approval_status !== "committed") {
      const editBtn = rightActions.createEl("button", {
        text: "Edit",
        cls: "spindle-btn-secondary",
      });
      editBtn.onClickEvent(() => {
        this.isEditing = true;
        this.render();
      });
    }

    // Approve Button
    if (
      this.suggestion.approval_status === "pending_author_approval" ||
      this.suggestion.approval_status === "validated"
    ) {
      const approveBtn = rightActions.createEl("button", {
        text: "Approve",
        cls: "spindle-btn-approve",
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

    // Commit to Vault Button (Enabled when APPROVED or EDITED)
    const canCommit =
      this.suggestion.approval_status === "approved" ||
      this.suggestion.approval_status === "edited";

    const commitBtn = rightActions.createEl("button", {
      text: "Commit to Vault Canon",
      cls: `spindle-btn-commit ${canCommit ? "is-active" : "is-disabled"}`,
    });
    commitBtn.disabled = !canCommit;

    commitBtn.onClickEvent(async () => {
      if (!canCommit) {
        new Notice("Suggestion must be Approved or Edited before committing to canon.");
        return;
      }

      commitBtn.disabled = true;
      commitBtn.setText("Committing to Vault...");

      try {
        const folder = this.plugin.settings.defaultDestinationFolder || "Manuscript/Side Stories";
        const commitResult = await this.plugin.client.commitSuggestion(this.suggestion.id, {
          destination_folder: folder,
        });

        // Write note safely into Obsidian vault
        await this.writeToVault(commitResult.file_path, commitResult.markdown_content);

        new Notice(`✓ Committed "${this.suggestion.title}" to ${commitResult.file_path}!`);
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
    editContainer.createEl("h3", { text: "Edit Suggestion", cls: "spindle-edit-title" });

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

    const btnRow = editContainer.createDiv({ cls: "spindle-modal-actions-bar" });
    const cancelBtn = btnRow.createEl("button", {
      text: "Cancel",
      cls: "spindle-btn-secondary",
    });
    cancelBtn.onClickEvent(() => {
      this.isEditing = false;
      this.render();
    });

    const saveBtn = btnRow.createEl("button", {
      text: "Save & Validate Edits",
      cls: "spindle-btn-approve",
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
  }

  /**
   * Safely writes committed content into the local vault, creating parent directories as necessary.
   */
  private async writeToVault(filePath: string, content: string): Promise<void> {
    const normalized = filePath.replace(/\\/g, "/");
    const parts = normalized.split("/");
    parts.pop()!;
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
