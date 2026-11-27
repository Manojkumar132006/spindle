# Autonomous Narrative Branch Exploration

Spindle's Branch Exploration feature allows fiction authors to discover divergent narrative trajectories at any point in their story without writing prompts.

---

## 1. Problem & Motivation

Traditional generative writing tools require the author to supply a detailed prompt explaining what should happen next. This creates cognitive fatigue when the author is experiencing writer's block or actively seeking fresh possibilities.

Spindle solves this by taking the current point-in-time `StoryState` (the characters present, established events, open threads, and vault lore) and autonomously synthesizing 2 to 5 divergent narrative pathways.

---

## 2. Dramatic Trajectory Taxonomy

The Branch Explorer categorizes divergent paths along distinct narrative angles:

1. **Tactical Escalation / Confrontation**:
   - The protagonist or antagonist makes an aggressive, decisive move.
   - Stakes escalate immediately, accelerating conflict.
2. **Covert Investigation / Stealth**:
   - Focuses on espionage, surveillance, and information gathering.
   - Pacing shifts toward tension, discovery, and suspense without immediate violence.
3. **Alliance / Diplomacy / Compromise**:
   - Competing factions or rivals are forced into negotiations or an uneasy temporary truce.
   - Explores moral ambiguity and shifting loyalties.
4. **Retreat / Regroup / Defensive Maneuver**:
   - A character recognizes an insurmountable obstacle or trap and chooses to fall back.
   - Shifts focus to recovery, logistics, and planning.
5. **Psychological Manipulation / Deception**:
   - A battle of wits utilizing false pretenses, rumors, or psychological leverage.

---

## 3. Exploration Pipeline

```
1. Author triggers "Explore Branches" at narrative position (e.g. pos 1.0)
                                 │
2. Spindle retrieves point-in-time StoryState from Database
   (Filters characters, events, and lore strictly up to that position)
                                 │
3. Story Architect LLM generates divergent BranchExplorerOption items
   (Enforces: Strict entity boundaries, 3 sequential beats, vault citations)
                                 │
4. ConstraintEngine validates each branch option in Python
   (Runs LifeStatus, Chronology, EntityExistence, Epistemic, WorldRule checks)
                                 │
5. Persisted as Suggestion records in database
   (approval_status: pending_author_approval)
                                 │
6. Rendered in Obsidian ExploreBranchesModal
   (Interactive cards with badges, beats, character pills, validation status)
                                 │
7. Author clicks "Review & Commit Branch"
   (Opens review modal to inspect diagnostics, edit text, and commit to vault)
```

---

## 4. Obsidian User Interface

The Obsidian plugin provides a dedicated modal (`ExploreBranchesModal`):
- **Access Points**:
  - Side pane **Story Overview** > **"🌿 Explore Branches"** button.
  - Command Palette (`Cmd/Ctrl + P`) > **"Spindle: Explore Narrative Branches (No Prompt Required)"**.
- **Controls**:
  - **Story Timeline Position**: Chronological point to branch from (e.g. `1.0`).
  - **Number of Divergent Pathways**: Dropdown selecting 2 to 5 branches.
  - **Focus Characters (Optional)**: Filter branches around specific cast members.
- **Card Elements**:
  - Title and dramatic angle badge (e.g. `TACTICAL ESCALATION`).
  - Concise premise.
  - 3-beat sequential outline.
  - Cast member pills.
  - Canon validation pill (`✓ Canon Validated` or `⚠ Advisory Warnings`).
  - **"Review & Commit Branch ➔"** action button.
