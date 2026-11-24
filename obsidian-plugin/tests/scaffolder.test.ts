import test from "node:test";
import assert from "node:assert/strict";
import { VaultScaffolder, SCAFFOLD_FOLDERS, TEMPLATES } from "../src/services/vaultScaffolder";

test("VaultScaffolder - scaffolds folders, templates, series bible, and configs non-destructively", async () => {
  const existingFiles = new Set<string>(["Manuscript"]);
  const fileContents = new Map<string, string>();
  const createdFolders: string[] = [];

  const mockApp: any = {
    vault: {
      adapter: {
        exists: async (path: string) => existingFiles.has(path),
        write: async (path: string, content: string) => {
          existingFiles.add(path);
          fileContents.set(path, content);
        },
        read: async (path: string) => fileContents.get(path) || "[]",
      },
      createFolder: async (folder: string) => {
        existingFiles.add(folder);
        createdFolders.push(folder);
      },
      create: async (path: string, content: string) => {
        existingFiles.add(path);
        fileContents.set(path, content);
      },
    },
  };

  const scaffolder = new VaultScaffolder(mockApp);
  const result = await scaffolder.scaffoldAll();

  // Manuscript was already existing, so skipped
  assert.ok(result.skipped.includes("Manuscript"));
  // Other folders should be created
  assert.ok(result.foldersCreated.includes("Characters"));
  assert.ok(result.foldersCreated.includes("Worldbuilding/Factions"));
  assert.ok(result.foldersCreated.includes("Templates"));

  // Templates created
  assert.ok(result.filesCreated.includes("Templates/Character.md"));
  assert.ok(result.filesCreated.includes("Templates/Scene.md"));
  assert.ok(result.filesCreated.includes("Series Bible.md"));
  assert.ok(result.filesCreated.includes("Start Here.md"));

  // Configs updated
  assert.ok(result.configsUpdated.includes(".obsidian/community-plugins.json"));
  assert.ok(result.configsUpdated.includes(".obsidian/plugins/templater-obsidian/data.json"));

  // Verify templater config content
  const templaterJson = JSON.parse(
    fileContents.get(".obsidian/plugins/templater-obsidian/data.json") || "{}"
  );
  assert.equal(templaterJson.templates_folder, "Templates");
  assert.equal(templaterJson.trigger_on_file_creation_mode, "folder");
  assert.ok(templaterJson.folder_templates.length > 0);

  // Verify community plugins content
  const pluginsJson = JSON.parse(
    fileContents.get(".obsidian/community-plugins.json") || "[]"
  );
  assert.ok(pluginsJson.includes("longform"));
  assert.ok(pluginsJson.includes("templater-obsidian"));
  assert.ok(pluginsJson.includes("dataview"));
  assert.ok(pluginsJson.includes("calendar"));
  assert.ok(pluginsJson.includes("spindle-narrative"));
});
