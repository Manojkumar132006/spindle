/**
 * Vault Scaffolder Service.
 * Bootstraps standard novel writing folder architecture, Markdown templates,
 * Series Bible dashboard, and plugin configurations (Templater, Dataview, Longform, Spindle).
 */

import type { App, TFile } from "obsidian";

export interface ScaffoldResult {
  foldersCreated: string[];
  filesCreated: string[];
  configsUpdated: string[];
  skipped: string[];
}

export const DEFAULT_FOLDER_TEMPLATES = [
  { folder: "Characters", template: "Templates/Character.md" },
  { folder: "Manuscript", template: "Templates/Scene.md" },
  { folder: "Manuscript/Side Stories", template: "Templates/Scene.md" },
  { folder: "Writing Log", template: "Templates/Writing Log.md" },
  { folder: "Worldbuilding/Locations", template: "Templates/Location.md" },
  { folder: "Worldbuilding/Factions", template: "Templates/Faction.md" },
  { folder: "Worldbuilding/Magic", template: "Templates/Magic.md" },
  { folder: "Worldbuilding/Peoples and Nations", template: "Templates/People or Nation.md" },
  { folder: "Plot/Timeline", template: "Templates/Event.md" },
];

export const SCAFFOLD_FOLDERS: string[] = [
  "Manuscript",
  "Manuscript/Side Stories",
  "Characters",
  "Worldbuilding",
  "Worldbuilding/Factions",
  "Worldbuilding/History",
  "Worldbuilding/Locations",
  "Worldbuilding/Magic",
  "Worldbuilding/Peoples and Nations",
  "Plot",
  "Plot/Outline",
  "Plot/Timeline",
  "Writing Log",
  "Research",
  "Templates",
];

export const TEMPLATES: Record<string, string> = {
  "Templates/Character.md": `---
type: character
role: protagonist
age: 
first-appearance: 
status: alive
aliases: []
tags:
  - character
---
# <% tp.file.title %>

## Summary
Brief description of the character, their identity, and core disposition.

## Core Motivation
What this character desires above all else, their internal and external conflicts.

## Key Relationships
- **Ally / Mentor**: 
- **Rival / Antagonist**: 

## Arc / Progression
- **Starting State**: 
- **Transformation Points**: 
- **Target Resolution**: 
`,

  "Templates/Scene.md": `---
type: scene
summary: 
pov: 
place: 
chapter: 1
act: 1
order: 1
goal: 
conflict: 
outcome: 
status: draft
tags:
  - scene
---
# <% tp.file.title %>

## Scene Setup
- **POV**: [[<% tp.frontmatter.pov %>]]
- **Location**: [[<% tp.frontmatter.place %>]]
- **Scene Goal**: What does the POV character want entering the scene?
- **Conflict / Obstacle**: What forces resist their pursuit?

## Narrative Beats
1. 
2. 
3. 

## Impact & Consequences
What changed permanently after this scene concludes?
`,

  "Templates/Event.md": `---
type: event
timeline-position: 1.0
participants: []
location: 
outcome: 
significance: major
tags:
  - event
---
# <% tp.file.title %>

## Summary
Key chronological occurrence that impacts the canon timeline.

## Chronological Context
- **Preceding Events**: 
- **Participants**: 
- **Location**: 

## Fallout
The irreversible consequences establishing constraints on future narrative arcs.
`,

  "Templates/Location.md": `---
type: location
region: 
faction-control: 
significance: 
tags:
  - location
  - worldbuilding
---
# <% tp.file.title %>

## Geography & Atmosphere
Sensory details, climate, architecture, and mood.

## Strategic & Political Significance
Who controls this place and why is it contested or valuable?

## Notable Landmarks & Residents
- 
`,

  "Templates/Faction.md": `---
type: faction
leader: 
headquarters: 
ideology: 
allies: []
enemies: []
tags:
  - faction
  - worldbuilding
---
# <% tp.file.title %>

## Core Ideology & Goals
What does this faction stand for, and what future are they striving to build?

## Resources & Leverage
Military, political, financial, or esoteric strength.

## Internal Factions & Tension
Dissenting leaders, sub-groups, or vulnerabilities.
`,

  "Templates/Magic.md": `---
type: magic-system
source: 
practitioners: 
limitations: 
tags:
  - magic
  - worldbuilding
---
# <% tp.file.title %>

## The Cost & Rules
- **Source of Power**: 
- **Hard Limitations**: What can this power NEVER do?
- **Cost / Price**: What must be paid or risked to invoke it?

## Cultural & Historical Role
How society perceives and regulates this power.
`,

  "Templates/People or Nation.md": `---
type: nation
culture: 
government: 
customs: 
tags:
  - worldbuilding
  - nation
---
# <% tp.file.title %>

## Culture & Customs
Belief systems, daily life, taboos, and traditions.

## History & Foreign Relations
Past wars, treaties, and standing grievances.
`,

  "Templates/Writing Log.md": `---
type: writing-log
date: <% tp.file.creation_date("YYYY-MM-DD") %>
word-count: 0
session-focus: 
tags:
  - writing-log
---
# Writing Log - <% tp.file.creation_date("YYYY-MM-DD") %>

- **Session Focus**: 
- **Words Written**: 
- **Scenes Worked On**: 

## Breakthroughs & Decisions
- 

## Next Session Objectives
- 
`,
};

export const SERIES_BIBLE_CONTENT: string = `---
type: bible
title: Series Bible & Story Dashboard
---
# Series Bible

Welcome to your Spindle-integrated Story Bible. Use this dashboard to navigate scenes, characters, and canon lore.

## 🎭 Characters
\`\`\`dataview
TABLE role as "Role", status as "Status", first-appearance as "First Appearance"
FROM "Characters"
WHERE type = "character"
SORT file.name ASC
\`\`\`

## 🎬 Manuscript & Scenes
\`\`\`dataview
TABLE act as "Act", chapter as "Chapter", order as "Order", pov as "POV", place as "Location", status as "Status"
FROM "Manuscript"
WHERE type = "scene"
SORT act ASC, chapter ASC, order ASC
\`\`\`

## 🏰 Worldbuilding Directory
\`\`\`dataview
TABLE type as "Category", tags as "Tags"
FROM "Worldbuilding"
SORT type ASC, file.name ASC
\`\`\`

## 📜 Timeline Events
\`\`\`dataview
TABLE timeline-position as "Position", location as "Location", outcome as "Outcome"
FROM "Plot"
WHERE type = "event"
SORT timeline-position ASC
\`\`\`
`;

export const START_HERE_CONTENT: string = `# Welcome to Spindle Story Project

Your novel vault has been scaffolded with standard fiction writing architecture and preconfigured for seamless authoring:

## 📁 Vault Structure
- **\`Manuscript/\`**: Your novel chapters and scenes. Compatible with Longform and Spindle scene extraction.
- **\`Characters/\`**: Character profile sheets with motivations, relationships, and progression arcs.
- **\`Worldbuilding/\`**: Factions, History, Locations, Magic Systems, and Peoples/Nations.
- **\`Plot/\`**: Outline and chronological timeline events.
- **\`Templates/\`**: Standard Templater templates pre-linked for quick scene and character creation.
- **\`Series Bible.md\`**: Live Dataview dashboard aggregating characters, scenes, and lore.

## ⚡ Spindle Commands
1. **Open Story Overview** (Ribbon icon or \`Cmd/Ctrl+P\` > \`Spindle: Open Story Overview\`): Live narrative health metrics, constraint checks, and character counts.
2. **Explore Branches** (\`Spindle: Explore Narrative Branches\`): Discover multiple divergent narrative paths without writing prompts.
3. **Generate with AI** (\`Spindle: Generate with AI\`): Generate plot points, side stories, or continuity reports checked against canon rules.
4. **Sync Vault** (\`Spindle: Sync Vault to Backend\`): Ingest all character profiles, scenes, and lore files into the Spindle graph.

## 🔌 Bundled & Recommended Community Plugins
- **Dataview**: Powers live queries in \`Series Bible.md\`.
- **Templater**: Auto-inserts frontmatter and date metadata into \`Templates/\`.
- **Longform**: Compile and reorder manuscript scenes into complete books.
- **Calendar**: Visual timeline tracking of daily writing logs.
- **Spindle Narrative**: Multi-agent constraint validation, continuity checking, and branch exploration.
`;

export class VaultScaffolder {
  private app: App;

  constructor(app: App) {
    this.app = app;
  }

  /**
   * Scaffolds the complete vault architecture, templates, series bible, and plugin configs.
   * Completely non-destructive: existing files are never overwritten.
   */
  public async scaffoldAll(): Promise<ScaffoldResult> {
    const result: ScaffoldResult = {
      foldersCreated: [],
      filesCreated: [],
      configsUpdated: [],
      skipped: [],
    };

    // 1. Create standard folder tree
    for (const folder of SCAFFOLD_FOLDERS) {
      const exists = await this.app.vault.adapter.exists(folder);
      if (!exists) {
        try {
          await this.app.vault.createFolder(folder);
          result.foldersCreated.push(folder);
        } catch {
          // Fallback if adapter creates directory
          try {
            await (this.app.vault.adapter as any).mkdir?.(folder);
            result.foldersCreated.push(folder);
          } catch {
            result.skipped.push(folder);
          }
        }
      } else {
        result.skipped.push(folder);
      }
    }

    // 2. Write Templates if missing
    for (const [path, content] of Object.entries(TEMPLATES)) {
      const exists = await this.app.vault.adapter.exists(path);
      if (!exists) {
        try {
          await this.app.vault.create(path, content);
          result.filesCreated.push(path);
        } catch {
          await this.app.vault.adapter.write(path, content);
          result.filesCreated.push(path);
        }
      } else {
        result.skipped.push(path);
      }
    }

    // 3. Write Series Bible if missing
    const biblePath = "Series Bible.md";
    if (!(await this.app.vault.adapter.exists(biblePath))) {
      try {
        await this.app.vault.create(biblePath, SERIES_BIBLE_CONTENT);
        result.filesCreated.push(biblePath);
      } catch {
        await this.app.vault.adapter.write(biblePath, SERIES_BIBLE_CONTENT);
        result.filesCreated.push(biblePath);
      }
    } else {
      result.skipped.push(biblePath);
    }

    // 4. Write Start Here if missing
    const startPath = "Start Here.md";
    if (!(await this.app.vault.adapter.exists(startPath))) {
      try {
        await this.app.vault.create(startPath, START_HERE_CONTENT);
        result.filesCreated.push(startPath);
      } catch {
        await this.app.vault.adapter.write(startPath, START_HERE_CONTENT);
        result.filesCreated.push(startPath);
      }
    } else {
      result.skipped.push(startPath);
    }

    // 5. Configure Community Plugins List (.obsidian/community-plugins.json)
    const commPluginsPath = ".obsidian/community-plugins.json";
    try {
      let pluginsList: string[] = [
        "longform",
        "templater-obsidian",
        "dataview",
        "calendar",
        "spindle-narrative",
      ];
      if (await this.app.vault.adapter.exists(commPluginsPath)) {
        const raw = await this.app.vault.adapter.read(commPluginsPath);
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          const merged = new Set([...parsed, ...pluginsList]);
          pluginsList = Array.from(merged);
        }
      }
      await this.app.vault.adapter.write(commPluginsPath, JSON.stringify(pluginsList, null, 2));
      result.configsUpdated.push(commPluginsPath);
    } catch (err) {
      console.warn("Spindle: Could not update community-plugins.json:", err);
    }

    // 6. Configure Templater Settings (.obsidian/plugins/templater-obsidian/data.json)
    const templaterConfigPath = ".obsidian/plugins/templater-obsidian/data.json";
    try {
      const templaterDir = ".obsidian/plugins/templater-obsidian";
      if (!(await this.app.vault.adapter.exists(templaterDir))) {
        try {
          await this.app.vault.createFolder(templaterDir);
        } catch {
          await (this.app.vault.adapter as any).mkdir?.(templaterDir);
        }
      }

      let templaterConfig: Record<string, any> = {
        data_version: 2,
        command_timeout: 5,
        templates_folder: "Templates",
        trigger_on_file_creation_mode: "folder",
        folder_templates: DEFAULT_FOLDER_TEMPLATES,
        syntax_highlighting: true,
        enabled_templates_hotkeys: [],
      };

      if (await this.app.vault.adapter.exists(templaterConfigPath)) {
        try {
          const raw = await this.app.vault.adapter.read(templaterConfigPath);
          const parsed = JSON.parse(raw);
          templaterConfig = {
            ...parsed,
            templates_folder: "Templates",
            trigger_on_file_creation_mode: "folder",
            folder_templates: DEFAULT_FOLDER_TEMPLATES,
          };
        } catch {
          // Use default
        }
      }

      await this.app.vault.adapter.write(
        templaterConfigPath,
        JSON.stringify(templaterConfig, null, 2)
      );
      result.configsUpdated.push(templaterConfigPath);
    } catch (err) {
      console.warn("Spindle: Could not configure Templater data.json:", err);
    }

    return result;
  }

  /**
   * Directly creates and opens a templated note in the vault, expanding template placeholders.
   */
  public async createTemplatedNote(
    folder: string,
    title: string,
    templateKey: string
  ): Promise<TFile | null> {
    const cleanTitle = title.replace(/[\\/*?:"<>|]/g, "").trim();
    if (!cleanTitle) return null;

    // Ensure target folder exists
    if (!(await this.app.vault.adapter.exists(folder))) {
      try {
        await this.app.vault.createFolder(folder);
      } catch {
        await (this.app.vault.adapter as any).mkdir?.(folder);
      }
    }

    const filePath = `${folder}/${cleanTitle}.md`;
    if (await this.app.vault.adapter.exists(filePath)) {
      const existing = this.app.vault.getAbstractFileByPath(filePath);
      return existing && "extension" in existing ? (existing as TFile) : null;
    }

    // Retrieve template text
    let templateContent = TEMPLATES[templateKey] || "";
    if (!templateContent && (await this.app.vault.adapter.exists(templateKey))) {
      templateContent = await this.app.vault.adapter.read(templateKey);
    }

    const nowIso = new Date().toISOString().split("T")[0];
    const expanded = templateContent
      .replace(/<%\s*tp\.file\.title\s*%>/g, cleanTitle)
      .replace(/<%\s*tp\.file\.creation_date\([^)]*\)\s*%>/g, nowIso)
      .replace(/<%\s*tp\.frontmatter\.[a-zA-Z0-9_-]+\s*%>/g, "")
      .replace(/<%\s*[^%]+\s*%>/g, "");

    const newFile = await this.app.vault.create(filePath, expanded);
    return newFile;
  }
}
