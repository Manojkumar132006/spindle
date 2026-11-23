"""Base models, mixins, and common enumeration types."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from spindle.database import Base


class CanonStatus(enum.StrEnum):
    """Canon status of extracted or created entities and events."""

    DRAFT = "draft"
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class KnowledgeStatus(enum.StrEnum):
    """Epistemic status of a character regarding a fact or event."""

    UNKNOWN = "unknown"
    SUSPECTED = "suspected"
    BELIEVED = "believed"
    CONFIRMED = "confirmed"
    FALSE_BELIEF = "false_belief"
    CONCEALED = "concealed"


class ConstraintType(enum.StrEnum):
    """Types of narrative constraints enforced by the engine."""

    CANON = "canon"
    WORLD_RULE = "world_rule"
    TEMPORAL = "temporal"
    CHARACTER_KNOWLEDGE = "character_knowledge"
    CHARACTER_BEHAVIOUR = "character_behaviour"
    NARRATIVE_DISCLOSURE = "narrative_disclosure"
    AUTHOR_PREFERENCE = "author_preference"


class ConstraintSeverity(enum.StrEnum):
    """Severity level of constraint violations."""

    HARD = "hard"
    SOFT = "soft"
    WARNING = "warning"


class EnforcementMethod(enum.StrEnum):
    """Method used to enforce constraint."""

    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"


class SuggestionType(enum.StrEnum):
    """Types of generated creative proposals."""

    PLOT_POINT = "plot_point"
    SIDE_STORY = "side_story"
    CONTINUITY_ANALYSIS = "continuity_analysis"


class ApprovalStatus(enum.StrEnum):
    """Lifecycle status of a generated creative suggestion."""

    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PENDING_AUTHOR_APPROVAL = "pending_author_approval"
    APPROVED = "approved"
    EDITED = "edited"
    COMMITTED = "committed"


class BranchType(enum.StrEnum):
    """Type of narrative branch."""

    MAIN = "main"
    WHAT_IF = "what_if"
    ALTERNATIVE = "alternative"


class BranchStatus(enum.StrEnum):
    """Status of narrative branch."""

    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"


class ThreadStatus(enum.StrEnum):
    """Status of a narrative arc or thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class DocumentType(enum.StrEnum):
    """Type of source document ingested from vault."""

    CHARACTER = "character"
    SCENE = "scene"
    EVENT = "event"
    LOCATION = "location"
    WORLDBUILDING = "worldbuilding"
    RESEARCH = "research"
    OUTLINE = "outline"
    GENERAL = "general"


class RuleType(enum.StrEnum):
    """Type of world rule."""

    MAGIC = "magic"
    PHYSICS = "physics"
    SOCIETAL = "societal"
    BIOLOGICAL = "biological"
    GENERAL = "general"


class EnforcementLevel(enum.StrEnum):
    """Enforcement level of a world rule."""

    HARD = "hard"
    SOFT = "soft"


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDBaseModel(Base, TimestampMixin):
    """Abstract base model with UUID primary key and timestamp mixin."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
