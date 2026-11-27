# Multi-Agent LangGraph Workflow

Spindle employs an 8-agent specialized cognitive architecture orchestrated via **LangGraph**. Rather than relying on a single monolithic LLM prompt that suffers from context degradation and hallucinated world facts, Spindle decomposes narrative generation into discrete analytical stages.

---

## 1. Architecture & State Graph

The generation pipeline executes a state machine defined in `backend/spindle/agents/graph.py`.

```
                    ┌─────────────────────────┐
                    │   Narrative Director    │
                    │   (Classifies & Scopes) │
                    └────────────┬────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
┌──────────▼──────────┐┌─────────▼─────────┐┌──────────▼──────────┐
│    Canon Analyst    ││ Character Analyst ││  Timeline Analyst   │
│ (Events & Precedent)││  (Psychology/Arc) ││ (Sequence/Presence) │
└──────────┬──────────┘└─────────┬─────────┘└──────────┬──────────┘
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Causal Reasoner     │
                    │  (Prerequisites/Stakes) │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Plot Architect      │
                    │   (Synthesizes Beats)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Constraint Validator   │◄────────┐
                    │ (Deterministic Engine)  │         │
                    └────────────┬────────────┘         │
                                 │                      │
                         Is Valid?                      │ Hard Failure
                         ┌───────┴───────┐              │ (Max 2 Revisions)
                         │               │              │
                     [PASS]            [FAIL] ──────────┘
                         │
                    ┌────▼────────────────────┐
                    │    Narrative Critic     │
                    │ (Plausibility / Scoring)│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Result Synthesizer   │
                    │   (Structured Output)   │
                    └─────────────────────────┘
```

---

## 2. Agent Roster & Responsibilities

### Agent 1: Narrative Director
- **Role:** Triage and mission coordinator.
- **Responsibilities:**
  - Classifies author requests (`plot_point`, `side_story`, or `continuity_analysis`).
  - Sets the analytical scope and boundary conditions.
  - Identifies target entities strictly from the author's established cast.
- **Strict Boundary:** Prohibited from introducing or assuming nonexistent characters.

### Agent 2: Canon Analyst
- **Role:** Archivist and lore continuity guardian.
- **Responsibilities:**
  - Cross-references established events up to the current narrative position.
  - Catalogs open narrative threads that could be advanced or resolved.
  - Queries active world rules and excerpts from vault notes.

### Agent 3: Character Analyst
- **Role:** Psychological coherence specialist.
- **Responsibilities:**
  - Evaluates character motivations, defense mechanisms, and emotional wounds.
  - Prevents epistemic leaks (characters must not act on information they have not learned).
  - Assesses relationship dynamics and behavioral plausibility.

### Agent 4: Timeline Analyst
- **Role:** Chronology and sequence specialist.
- **Responsibilities:**
  - Decouples manuscript order from in-world chronology.
  - Verifies character physical availability (characters cannot appear in two distant locations simultaneously without transit).
  - Confirms mortality state (deceased characters cannot appear outside of flashbacks/memories).

### Agent 5: Causal Reasoner
- **Role:** Cause-and-effect projector.
- **Responsibilities:**
  - Identifies strict preconditions required for the proposal to occur.
  - Forecasts downstream ripple effects and narrative stakes.
  - Ensures consequences irreversibly alter the story state.

### Agent 6: Plot Architect
- **Role:** Creative synthesist and beat author.
- **Responsibilities:**
  - Combines insights from Agents 2–5 into an actionable scene proposal.
  - Constructs 3 sequential, high-tension scene beats.
  - Cites vault documents as supporting evidence.
  - **Entity Boundary Enforcement:** Strictly limited to established characters. Minor background extras are permitted only by generic descriptive title (e.g. "the train conductor").
  - **Self-Correction:** If revision notes are received from the Constraint Validator, the architect actively modifies the proposal to resolve every reported violation.

### Agent 7: Constraint Validator
- **Role:** Rule verification gatekeeper.
- **Responsibilities:**
  - Executes the deterministic `ConstraintEngine` in Python.
  - Checks for hard rule violations (mortality, unestablished character hallucinations, unearned knowledge, chronological impossibilities).
  - Emits detailed diagnostic reports with rule IDs, offending evidence, and remediation hints.

### Agent 8: Narrative Critic
- **Role:** Literary quality and plausibility reviewer.
- **Responsibilities:**
  - Evaluates narrative plausibility, originality, and pacing.
  - Flags clichés or artificial conveniences.
  - Ensures the proposal meaningfully advances the protagonist's or antagonist's arc.

---

## 3. Self-Correction & Feedback Loop

When Agent 7 (Constraint Validator) identifies a `HARD` constraint violation (e.g. an unestablished character was introduced, or an event relies on unlearned knowledge):
1. The state graph triggers a conditional routing edge: `should_revise`.
2. The validator appends specific remediation notes into `revision_notes` in the graph state.
3. The graph loops back to Agent 6 (Plot Architect) with explicit instructions to fix the exact violations.
4. A maximum revision limit (default: 2 iterations) prevents infinite loops. If violations persist after maximum revisions, the suggestion is finalized with `is_valid: false` and the full diagnostic report is presented transparently to the author.
