/**
 * Spindle Plugin Settings Tab & Configuration.
 */

import { App, Notice, PluginSettingTab, Setting } from "obsidian";
import type { SpindlePlugin } from "./main";
import { VaultScaffolder } from "./services/vaultScaffolder";
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
    let projectInputEl: any;
    new Setting(containerEl)
      .setName("Project ID")
      .setDesc("UUID of the active story project. Leave blank or click 'Auto-Detect' to use current project.")
      .addText((text) => {
        projectInputEl = text;
        text
          .setPlaceholder("e.g. 123e4567-e89b-12d3-a456-426614174000")
          .setValue(this.plugin.settings.projectId)
          .onChange(async (value) => {
            this.plugin.settings.projectId = value.trim();
            await this.plugin.saveSettings();
          });
      })
      .addButton((button) =>
        button
          .setButtonText("Auto-Detect Project")
          .onClick(async () => {
            button.setDisabled(true);
            try {
              const overview = await this.plugin.client.getStoryOverview();
              if (overview?.project_id) {
                this.plugin.settings.projectId = overview.project_id;
                await this.plugin.saveSettings();
                projectInputEl.setValue(overview.project_id);
                new Notice(
                  `Auto-detected project: ${overview.project_name || overview.project_id}`
                );
              }
            } catch (err: any) {
              new Notice(`Failed to auto-detect project: ${err.message}`);
            } finally {
              button.setDisabled(false);
            }
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

    // Vault Scaffolding & Setup Section
    containerEl.createEl("h3", { text: "Story Vault Scaffolding & Templates" });
    new Setting(containerEl)
      .setName("Initialize Story Vault Architecture")
      .setDesc(
        "Creates standard novel folders (Manuscript, Characters, Worldbuilding, Plot, Research, Templates), standard templates, Series Bible, and configures Templater and community plugins."
      )
      .addButton((button) =>
        button
          .setButtonText("📁 Scaffold Vault Structure")
          .onClick(async () => {
            button.setDisabled(true);
            button.setButtonText("Scaffolding...");
            try {
              const scaffolder = new VaultScaffolder(this.app);
              const res = await scaffolder.scaffoldAll();
              new Notice(
                `Vault Scaffolding Complete!\n• Folders created: ${res.foldersCreated.length}\n• Templates & documents: ${res.filesCreated.length}\n• Configurations updated: ${res.configsUpdated.length}`
              );
            } catch (err: any) {
              new Notice(`Failed to scaffold vault: ${err.message}`);
            } finally {
              button.setDisabled(false);
              button.setButtonText("📁 Scaffold Vault Structure");
            }
          })
      );
  }
}
