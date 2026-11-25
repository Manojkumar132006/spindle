/**
 * Simple modal for prompting user text input (character names, scene titles, etc.).
 */

import { App, Modal, Setting } from "obsidian";

export class PromptModal extends Modal {
  private titleText: string;
  private placeholder: string;
  private value: string = "";
  private onSubmit: (result: string) => void;

  constructor(
    app: App,
    titleText: string,
    placeholder: string,
    onSubmit: (result: string) => void
  ) {
    super(app);
    this.titleText = titleText;
    this.placeholder = placeholder;
    this.onSubmit = onSubmit;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("spindle-modal-content");

    contentEl.createEl("h3", { text: this.titleText, cls: "spindle-modal-title" });

    new Setting(contentEl)
      .setName(this.titleText)
      .addText((text) => {
        text.setPlaceholder(this.placeholder);
        text.onChange((val) => {
          this.value = val;
        });
        text.inputEl.focus();
        text.inputEl.addEventListener("keydown", (e: KeyboardEvent) => {
          if (e.key === "Enter" && this.value.trim()) {
            e.preventDefault();
            this.close();
            this.onSubmit(this.value.trim());
          }
        });
      });

    const actionsEl = contentEl.createDiv({ cls: "spindle-modal-actions-bar" });
    const cancelBtn = actionsEl.createEl("button", {
      text: "Cancel",
      cls: "spindle-btn-secondary",
    });
    cancelBtn.onClickEvent(() => {
      this.close();
    });

    const submitBtn = actionsEl.createEl("button", {
      text: "Create Note",
      cls: "spindle-btn-commit is-active",
    });
    submitBtn.onClickEvent(() => {
      if (this.value.trim()) {
        this.close();
        this.onSubmit(this.value.trim());
      }
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
