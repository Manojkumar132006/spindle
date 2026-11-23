import test from "node:test";
import assert from "node:assert/strict";
import { VaultScanner } from "../src/services/vaultScanner";

test("VaultScanner - scans markdown files while excluding system and template folders", async () => {
  const mockFiles = [
    { path: "Manuscript/Act 1/Scene 1.md" },
    { path: "Worldbuilding/Characters/Elena.md" },
    { path: ".obsidian/workspace.json" },
    { path: ".obsidian/plugins/spindle/main.js" },
    { path: ".trash/Deleted Note.md" },
    { path: "Templates/Scene Template.md" },
  ];

  const mockApp: any = {
    vault: {
      getMarkdownFiles: () => mockFiles as any[],
      read: async (file: any) => `# Content for ${file.path}\n[[Elena Vareth]] was here.`,
    },
  };

  const scanner = new VaultScanner(mockApp);
  const result = await scanner.scanVault();

  // Excluded: .obsidian, .trash, Templates
  // Included: Manuscript/Act 1/Scene 1.md, Worldbuilding/Characters/Elena.md
  assert.equal(result.totalScanned, 2);
  assert.equal(result.files.length, 2);
  assert.equal(result.files[0].file_path, "Manuscript/Act 1/Scene 1.md");
  assert.ok(result.files[0].content_hash);
  assert.ok(result.files[0].content.includes("[[Elena Vareth]]"));
  assert.equal(result.files[1].file_path, "Worldbuilding/Characters/Elena.md");
  assert.equal(result.totalSkipped, 4);
});
