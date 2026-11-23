/**
 * Vault Scanner service for traversing Obsidian vault files and preparing sync payloads.
 */

import { App, TFile } from "obsidian";
import { SyncFileInput } from "../types";

export interface ScanResult {
  files: SyncFileInput[];
  totalScanned: number;
  totalSkipped: number;
}

export class VaultScanner {
  private app: App;

  constructor(app: App) {
    this.app = app;
  }

  /**
   * Scan all markdown files in the vault and format them for the Spindle backend sync endpoint.
   */
  public async scanVault(options?: {
    excludedFolders?: string[];
  }): Promise<ScanResult> {
    const excluded = options?.excludedFolders || [
      ".obsidian",
      ".trash",
      ".git",
      "Templates",
    ];

    const markdownFiles = this.app.vault.getMarkdownFiles();
    const syncFiles: SyncFileInput[] = [];
    let skipped = 0;

    for (const file of markdownFiles) {
      if (this.isExcluded(file.path, excluded)) {
        skipped++;
        continue;
      }

      try {
        const content = await this.app.vault.read(file);
        const hash = await this.calculateHash(content);

        syncFiles.push({
          path: file.path,
          file_path: file.path,
          content,
          content_hash: hash,
        });
      } catch (err) {
        console.error(`Spindle: Failed to read file ${file.path}:`, err);
        skipped++;
      }
    }

    return {
      files: syncFiles,
      totalScanned: syncFiles.length,
      totalSkipped: skipped,
    };
  }

  private isExcluded(path: string, excludedFolders: string[]): boolean {
    const normalized = path.replace(/\\/g, "/");
    return excludedFolders.some((folder) => {
      const cleanFolder = folder.replace(/^\/+|\/+$/g, "");
      return (
        normalized.startsWith(cleanFolder + "/") ||
        normalized === cleanFolder ||
        normalized.includes("/." + cleanFolder)
      );
    });
  }

  /**
   * Deterministic SHA-256 string hash for client-side change detection.
   */
  private async calculateHash(text: string): Promise<string> {
    if (typeof crypto !== "undefined" && crypto.subtle) {
      const encoder = new TextEncoder();
      const data = encoder.encode(text);
      const hashBuffer = await crypto.subtle.digest("SHA-256", data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    }
    // Fallback simple checksum if SubtleCrypto is unavailable
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash |= 0;
    }
    return Math.abs(hash).toString(16);
  }
}
