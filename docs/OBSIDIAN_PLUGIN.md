# Obsidian Desktop Plugin & Scaffolding Guide

The Spindle Obsidian plugin connects the author's local desktop writing environment to the Spindle narrative intelligence backend. It provides side-pane story health metrics, AI generation modals, autonomous branch exploration, non-destructive canon commitment, and one-click vault scaffolding with Templater integration.

---

## 1. Directory Structure & Architecture

Located in `obsidian-plugin/`:
```
obsidian-plugin/
├── src/
│   ├── api/
│   │   └── backendClient.ts         # Typed REST client with error parsing & fallback
│   ├── modals/
│   │   ├── exploreBranchesModal.ts  # Visual card browser for divergent pathways
│   │   ├── generateModal.ts         # Targeted generation modal (Plot, Side Story, Continuity)
│   │   ├── promptModal.ts           # Clean text input dialog for note creation
│   │   └── suggestionReviewModal.ts # Review gate with validator diagnostics & commit action
│   ├── services/
│   │   ├── vaultScanner.ts          # Traverses vault markdown files with change hashing
│   │   └── vaultScaffolder.ts       # Bootstraps folder trees, templates, & plugin configs
│   ├── views/
│   │   └── storyOverviewView.ts     # Side-panel dashboard with live story metrics
│   ├── main.ts                      # Plugin lifecycle, command registration, ribbon icons
│   ├── settings.ts                  # Plugin configuration tab
│   └── types/index.ts               # TypeScript interfaces matching backend models
├── styles.css                       # Obsidian native theme styling (light & dark compatible)
├── esbuild.config.mjs               # Fast bundle build script producing main.js
└── package.json
```

---

## 2. Vault Scaffolding & Community Plugin Setup

When setting up a new story vault, an author can initialize the entire writing infrastructure with a single click via **`Spindle: Scaffold Story Vault Structure & Templates`** or the **"📁 Scaffold Vault"** button.

### 1. Created Folder Structure
- `Manuscript/` & `Manuscript/Side Stories/`: Novel prose chapters and scenes.
- `Characters/`: Dedicated character profiles with psychological arcs.
- `Worldbuilding/`: Categorized lore:
  - `Factions/`
  - `History/`
  - `Locations/`
  - `Magic/`
  - `Peoples and Nations/`
- `Plot/`: Story structure (`Outline/`, `Timeline/`).
- `Writing Log/`: Daily writing sessions and word count logs.
- `Research/`: Real-world reference notes.
- `Templates/`: Fiction templates pre-configured for Templater.

### 2. Pre-Packaged Templates (`Templates/`)
- `Character.md`: Concept, Appearance, Relationships, Psychology (Values, Wound, Defenses), Trajectory (Flaws, Lens, Arc).
- `Scene.md`: POV, Location, Goal, Conflict, Outcome, Narrative Beats, and Fallout.
- `Event.md`: Timeline position, participants, location, outcome, significance.
- `Location.md`, `Faction.md`, `Magic.md`, `People or Nation.md`, `Writing Log.md`.

### 3. Live Series Bible (`Series Bible.md`)
Includes live Dataview table queries aggregating:
- 🎭 **Characters Table**: role, status, first appearance.
- 🎬 **Manuscript Table**: act, chapter, order, POV, location, status.
- 🏰 **Worldbuilding Directory**: category, tags.
- 📜 **Timeline Events**: chronological position, outcome.

---

## 3. Templater Integration & Automatic Folder Triggers

The scaffolder automatically writes `.obsidian/plugins/templater-obsidian/data.json` to configure:
1. `"templates_folder": "Templates"`
2. `"trigger_on_file_creation_mode": "folder"`
3. `"folder_templates"`:
   - `Characters` $\to$ `Templates/Character.md`
   - `Manuscript` $\to$ `Templates/Scene.md`
   - `Writing Log` $\to$ `Templates/Writing Log.md`
   - `Worldbuilding/Locations` $\to$ `Templates/Location.md`
   - `Worldbuilding/Factions` $\to$ `Templates/Faction.md`
   - `Worldbuilding/Magic` $\to$ `Templates/Magic.md`
   - `Worldbuilding/Peoples and Nations` $\to$ `Templates/People or Nation.md`
   - `Plot/Timeline` $\to$ `Templates/Event.md`

Whenever a new note is created inside any of these folders in Obsidian, Templater automatically formats it with the correct frontmatter and headings.

---

## 4. Spindle Commands Reference

Available in the Obsidian Command Palette (`Cmd/Ctrl + P`):

1. **`Spindle: Open Story Overview`**: Opens or focuses the side-pane narrative dashboard.
2. **`Spindle: Explore Narrative Branches (No Prompt Required)`**: Launches the branch exploration modal.
3. **`Spindle: Generate with AI (Plot Point, Side Story, Continuity)`**: Launches the custom prompt generation modal.
4. **`Spindle: Sync Vault to Backend`**: Manually triggers incremental change detection and database sync.
5. **`Spindle: Review Suggestions`**: Opens the review gate for the most recent pending suggestion.
6. **`Spindle: Scaffold Story Vault Structure & Templates`**: Verifies and creates all folders, templates, and plugin settings.
7. **`Spindle: Create New Character Note`**: Prompts for a name and creates a templated note in `Characters/`.
8. **`Spindle: Create New Scene Note`**: Prompts for a title and creates a templated note in `Manuscript/`.
9. **`Spindle: Create New Writing Log Note`**: Creates and opens today's dated session log.

---

## 5. Non-Destructive Canon Commitment

When an author approves a suggestion and clicks **"Commit to Vault Canon"**:
1. Spindle calls `POST /api/v1/suggestions/{id}/commit`.
2. The backend generates native Obsidian Markdown with frontmatter (`type: scene`, `status: canon`, `source_suggestion_id: ...`).
3. It determines a non-colliding file path in `Manuscript/Side Stories/` (e.g. `Scene Title.md` or `Scene Title (2).md`), ensuring existing prose is never overwritten.
4. The new note is indexed into the database and created in the vault.
