/**
 * Core type definitions for Spindle Obsidian Plugin.
 */

export type SuggestionType = "plot_point" | "side_story" | "continuity_analysis";

export type ApprovalStatus =
  | "generated"
  | "validating"
  | "validated"
  | "pending_author_approval"
  | "approved"
  | "edited"
  | "rejected"
  | "committed";

export type ConstraintSeverity = "hard_failure" | "soft_warning" | "advisory";

export interface ConstraintIssue {
  severity: ConstraintSeverity;
  rule_type: string;
  message: string;
  involved_entities: string[];
}

export interface DiagnosticItem {
  rule_id?: string;
  rule_name: string;
  outcome: "PASS" | "FAIL" | "WARNING";
  severity?: string;
  message: string;
  evidence?: string[];
  remediation_hint?: string | null;
}

export interface ValidatorResult {
  validator_name: string;
  outcome: "PASS" | "FAIL" | "WARNING";
  issues: ConstraintIssue[];
}

export interface ValidationReport {
  overall_outcome: "PASS" | "FAIL" | "WARNING";
  is_valid?: boolean;
  has_hard_failures: boolean;
  summary?: string;
  passed_count?: number;
  failed_count?: number;
  warning_count?: number;
  total_issues?: number;
  diagnostics?: DiagnosticItem[];
  validator_results?: ValidatorResult[];
  results?: ValidatorResult[];
}

export interface Suggestion {
  id: string;
  project_id: string;
  suggestion_type: SuggestionType;
  title: string;
  premise: string;
  detailed_content: {
    act?: number;
    involved_characters?: string[];
    scene_beats?: string[];
    beats?: string[];
    beat?: string;
    narrative_impact?: string;
    historical_revisions?: string[];
    author_notes?: string[];
    [key: string]: any;
  };
  supporting_evidence: string[];
  assumptions: string[];
  validation_results?: ValidationReport;
  approval_status: ApprovalStatus;
  rejection_reason?: string;
  author_edits?: string;
  branch_id?: string;
  created_at?: string;
}

export interface StoryOverview {
  project_id: string;
  project_name: string;
  character_count: number;
  event_count: number;
  location_count: number;
  active_constraints: number;
  unresolved_threads: number;
  total_documents: number;
}

export interface SyncFileInput {
  path: string;
  file_path?: string;
  content: string;
  content_hash?: string;
  document_type?: string;
}

export interface VaultSyncResponse {
  status: string;
  total_files?: number;
  indexed_files?: number;
  total_files_received?: number;
  indexed_count?: number;
  errors: string[];
}

export interface CommitSuggestionResponse {
  status: string;
  suggestion_id: string;
  project_id: string;
  file_path: string;
  content_hash: string;
  document_id: string;
  event_id: string;
  markdown_content: string;
  committed_at: string;
}

export interface EditSuggestionRequest {
  title?: string;
  premise?: string;
  detailed_content?: Record<string, any>;
  edit_summary?: string;
}

export interface CommitSuggestionRequest {
  destination_folder?: string;
}

export interface SpindleSettings {
  backendUrl: string;
  projectId: string;
  defaultDestinationFolder: string;
  autoSyncOnSave: boolean;
  defaultNarrativePosition: number;
}
