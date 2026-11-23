# Spindle Obsidian Plugin

Native TypeScript desktop plugin for [Obsidian](https://obsidian.md) integrating the Spindle Narrative Intelligence system.

---

## Features

- **Vault Synchronizer:** Scans vault markdown files, extracts YAML frontmatter and `[[WikiLinks]]`, and pushes changed notes to Spindle narrative engine.
- **Story Overview Side Pane (`book-open` icon):** Visualizes character count, chronological events, locations, active constraints, and open threads.
- **Multi-Mode Generation Modal:** Request context-grounded plot points, side stories, or continuity checks directly from your editor.
- **Suggestion Review & Constraint Inspector:**
  - View proposed outline beats and supporting canon sources.
  - Review deterministic constraint validation diagnostics (Pass / Warning / Fail).
  - Approve, Edit (with historical revisions), or Reject (with mandatory reason).
  - **Non-Destructive Commitment:** Writes approved suggestions directly into your vault as native Markdown notes without altering existing manuscripts.

---

## Building & Installing

### 1. Requirements

- Node.js 18+
- npm

### 2. Build from Source

```bash
cd obsidian-plugin

# Install dependencies
npm install

# Run typechecks and unit tests
npm run typecheck
npm test

# Build production bundle (generates main.js)
npm run build
```

### 3. Installation into an Obsidian Vault

1. Create a plugin directory in your vault:
   ```bash
   mkdir -p /path/to/your/vault/.obsidian/plugins/spindle-narrative
   ```
2. Copy `main.js`, `manifest.json`, and `styles.css` into that directory:
   ```bash
   cp main.js manifest.json styles.css /path/to/your/vault/.obsidian/plugins/spindle-narrative/
   ```
   *(Or create a symlink from your vault's plugins folder to `obsidian-plugin/`)*
3. In Obsidian, go to **Settings** -> **Community plugins** -> enable **Spindle Narrative Intelligence**.
4. In **Settings** -> **Spindle**, set Backend API URL to `http://localhost:8000` and click **Test Connection**.
