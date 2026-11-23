/**
 * Spindle Plugin Settings Tab & Configuration.
 */

import { App, Notice, PluginSettingTab, Setting } from "obsidian";
import type { SpindlePlugin } from "./main";
import { SpindleSettings } from "./types";

export const DEFAULT_SETTINGS: SpindleSettings = {
  backendUrl: "http://localhost:8000",
  projectId: "",
  defaultDestinationFolder: "Manuscript/Side Stories",
  autoSyncOnSave: false,
  defaultNarrativePosition: 1.0,
};

export class SpindleSettingTab extends PluginSettingTab {
  private plugin: SpindlePlugin;

  constructor(app: App, plugin: SpindlePlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "Spindle Narrative Intelligence Settings" });

    // Backend URL
    let connectionStatusEl: HTMLElement;
    new Setting(containerEl)
      .setName("Backend API URL")
      .setDesc("Base URL of the Spindle FastAPI backend service.")
      .addText((text) =>
        text
          .setPlaceholder("http://localhost:8000")
          .setValue(this.plugin.settings.backendUrl)
          .onChange(async (value) => {
            this.plugin.settings.backendUrl = value.trim();
            await this.plugin.saveSettings();
          })
      )
      .addButton((button) =>
        button
          .setButtonText("Test Connection")
          .setCta()
          .onClick(async () => {
            button.setDisabled(true);
            button.setButtonText("Connecting...");
            connectionStatusEl.setText("Testing connection...");
            connectionStatusEl.className = "spindle-status-testing";

            try {
              const res = await this.plugin.client.checkHealth();
              connectionStatusEl.setText(
                `✓ Connected (${res.status || "healthy"}, env: ${res.environment || "dev"})`
              );
              connectionStatusEl.className = "spindle-status-connected";
              new Notice("Spindle backend connected successfully!");
            } catch (err: any) {
              connectionStatusEl.setText(`✗ Connection failed: ${err.message}`);
              connectionStatusEl.className = "spindle-status-error";
              new Notice(`Connection failed: ${err.message}`);
            } finally {
              button.setDisabled(false);
              button.setButtonText("Test Connection");
            }
          })
      );

    connectionStatusEl = containerEl.createDiv({ cls: "spindle-connection-status" });
    connectionStatusEl.setText("Click 'Test Connection' to verify backend link.");

    // Project ID
    new Setting(containerEl)
      .setName("Project ID")
      .setDesc("UUID of the active story project. All queries and sync events use this context.")
      .addText((text) =>
        text
          .setPlaceholder("e.g. 123e4567-e89b-12d3-a456-426614174000")
          .setValue(this.plugin.settings.projectId)
          .onChange(async (value) => {
            this.plugin.settings.projectId = value.trim();
            await this.plugin.saveSettings();
          })
      );

    // Default Destination Folder
    new Setting(containerEl)
      .setName("Default Destination Folder")
      .setDesc("Vault directory where approved suggestions are committed as new Markdown documents.")
      .addText((text) =>
        text
          .setPlaceholder("Manuscript/Side Stories")
          .setValue(this.plugin.settings.defaultDestinationFolder)
          .onChange(async (value) => {
            this.plugin.settings.defaultDestinationFolder = value.trim();
            await this.plugin.saveSettings();
          })
      );

    // Default Narrative Position
    new Setting(containerEl)
      .setName("Default Narrative Position")
      .setDesc("Normalized timeline position (e.g. 1.0 = beginning, 5.0 = midpoint, 10.0 = climax).")
      .addText((text) =>
        text
          .setPlaceholder("1.0")
          .setValue(String(this.plugin.settings.defaultNarrativePosition))
          .onChange(async (value) => {
            const num = parseFloat(value);
            if (!isNaN(num)) {
              this.plugin.settings.defaultNarrativePosition = num;
              await this.plugin.saveSettings();
            }
          })
      );

    // Auto-Sync Toggle
    new Setting(containerEl)
      .setName("Auto-Sync on File Save")
      .setDesc("Automatically sync changed markdown files with Spindle narrative state when saved.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.autoSyncOnSave)
          .onChange(async (value) => {
            this.plugin.settings.autoSyncOnSave = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
