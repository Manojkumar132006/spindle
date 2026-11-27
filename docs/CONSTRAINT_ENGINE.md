# Spindle Constraint Engine

The Spindle Constraint Engine is a deterministic verification system responsible for guaranteeing that creative proposals never violate established fictional canon or author-defined rules. 

Unlike traditional LLM wrappers that rely on prompt instructions to avoid mistakes, Spindle's Constraint Engine executes **compiled Python logic** against a point-in-time snapshot of the narrative graph (`StoryState`).

---

## 1. Core Architecture

The engine is located at `backend/spindle/core/constraints/` and consists of:
- **`BaseConstraintValidator`**: Abstract base class requiring an asynchronous `validate(proposal, story_state)` method returning a list of `ValidationDiagnostic`.
- **`ConstraintEngine`**: Orchestrator executing all registered validators and computing an aggregated `ValidationReport`.
- **`ValidationReport`**: Structured payload containing `overall_outcome` (`PASS`, `FAIL`, `WARNING`, `INSUFFICIENT_CONTEXT`), hard failure flags, and granular diagnostic items.

---

## 2. Deterministic Validators

### 1. `EntityExistenceValidator` (`deterministic/entity_existence.py`)
- **Purpose:** Prevents character hallucinations and enforces strict cast boundaries.
- **Rules Evaluated:**
  - Extracts all characters from `involved_characters` or `participants`.
  - Normalizes names and checks against the author's established characters (including configured aliases).
  - Permits standard generic functional roles (e.g. `guard`, `conductor`, `attendant`, `crowd`, `courier`, `stranger`).
  - **Outcome:** If an unestablished proper name (e.g. "Aldric Voss", "Marcus") appears, flags a `ConstraintSeverity.HARD` failure:
    `"Character '<name>' does not exist in the author's established story cast. Only established characters or generic role titles are permitted."`

### 2. `LifeStatusValidator` (`deterministic/life_status.py`)
- **Purpose:** Prevents deceased characters from actively participating in physical scenes.
- **Rules Evaluated:**
  - Checks each character's `current_state` (e.g. `alive`, `deceased`, `missing`).
  - Checks if the scene is flagged as an allowed exception (e.g. `flashback`, `memory`, `dream`, `vision`, `hallucination`, `corpse`).
  - **Outcome:** Deceased participation in a non-exempt scene produces a `HARD` failure blocking canon commitment.

### 3. `EpistemicValidator` (`deterministic/epistemic.py`)
- **Purpose:** Prevents epistemic leaks and dramatic irony violations (characters acting on secrets they have not learned).
- **Rules Evaluated:**
  - Queries `CharacterKnowledge` up to the scene's `narrative_position`.
  - If a scene requires a character to act upon a specific secret or plot truth, verifies that the character acquired confirmed knowledge of that fact prior to this narrative position.
  - **Outcome:** Unearned knowledge produces a `HARD` failure with clear provenance tracing.

### 4. `ChronologyValidator` (`deterministic/chronology.py`)
- **Purpose:** Guarantees causal prerequisites have been established earlier in story time.
- **Rules Evaluated:**
  - Compares the proposal's `preconditions` and `causal_dependencies` against preceding events in `story_state.established_events`.
  - Verifies that narrative order aligns with chronological dependencies.
  - **Outcome:** Missing prerequisite events result in a `HARD` failure requiring the author or AI to establish the antecedent scene first.

### 5. `WorldRuleValidator` (`deterministic/world_rule.py`)
- **Purpose:** Enforces universe-wide physics, magic, societal, and technological laws.
- **Rules Evaluated:**
  - Matches proposal actions, tags, and text against active `WorldRule` records in the project.
  - Differentiates between `EnforcementLevel.HARD` (strict physics/magic laws that produce `FAIL`) and `EnforcementLevel.SOFT` (cultural taboos or societal norms that produce `WARNING`).

---

## 3. Severity Levels & Report Outcomes

### Severity Levels (`ConstraintSeverity`):
1. **`HARD`**: Non-negotiable canon violation (e.g. deceased character presence, character hallucination, magic impossibility). Blocks automatic commitment.
2. **`SOFT`**: Thematic tension, behavioral inconsistency, or advisory caution. Permitted if author explicitly acknowledges the choice.
3. **`ADVISORY`**: Style suggestions or pacing notes.

### Aggregated Report Outcomes (`ValidationOutcome`):
- **`PASS`**: 0 failures, 0 warnings. Proposal is 100% canon-compliant.
- **`WARNING`**: 0 hard failures, but 1 or more soft/advisory warnings.
- **`FAIL`**: 1 or more hard failures. Proposal cannot be committed to canon without revisions.
- **`INSUFFICIENT_CONTEXT`**: Required story state attributes are missing.

---

## 4. Diagnostic Item Structure

Every diagnostic emitted by the Constraint Engine adheres to a typed schema:
```json
{
  "rule_id": "DETERMINISTIC_ENTITY_EXISTENCE_UNKNOWN_CHARACTER",
  "rule_name": "Unestablished Character Hallucination",
  "outcome": "FAIL",
  "severity": "hard",
  "message": "Character 'Garrick' does not exist in the author's established story cast. Available characters are: Billy.",
  "evidence": ["Proposing entity: Garrick"],
  "remediation_hint": "Replace 'Garrick' with one of the established characters (Billy) or refer to them generically."
}
```
This diagnostic is surfaced directly in the Obsidian suggestion review modal, allowing authors to see exactly why a rule failed and how to remediate it.
