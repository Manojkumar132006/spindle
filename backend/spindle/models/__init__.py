"""Spindle ORM models and schema declarations."""

from spindle.database import Base
from spindle.models.base import (
    ApprovalStatus,
    BranchStatus,
    BranchType,
    CanonStatus,
    ConstraintSeverity,
    ConstraintType,
    DocumentType,
    EnforcementLevel,
    EnforcementMethod,
    KnowledgeStatus,
    RuleType,
    SuggestionType,
    ThreadStatus,
    TimestampMixin,
    UUIDBaseModel,
)
from spindle.models.constraint import Constraint
from spindle.models.document import DocumentExcerpt, SourceDocument
from spindle.models.entity import Character, Location, Relationship, WorldRule
from spindle.models.event import Event, NarrativeThread
from spindle.models.knowledge import CharacterKnowledge
from spindle.models.project import Project
from spindle.models.suggestion import (
    NarrativeBranch,
    Suggestion,
    SuggestionRevision,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDBaseModel",
    "CanonStatus",
    "KnowledgeStatus",
    "ConstraintType",
    "ConstraintSeverity",
    "EnforcementMethod",
    "SuggestionType",
    "ApprovalStatus",
    "BranchType",
    "BranchStatus",
    "ThreadStatus",
    "DocumentType",
    "RuleType",
    "EnforcementLevel",
    "Project",
    "SourceDocument",
    "DocumentExcerpt",
    "Character",
    "Location",
    "WorldRule",
    "Relationship",
    "Event",
    "NarrativeThread",
    "CharacterKnowledge",
    "Constraint",
    "NarrativeBranch",
    "Suggestion",
    "SuggestionRevision",
]
