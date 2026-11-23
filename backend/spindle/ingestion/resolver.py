"""Entity resolution and stable ID lookup across Obsidian note titles and aliases."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from spindle.ingestion.wikilinks import clean_link_target


@dataclass
class ResolvedEntity:
    """Cached representation of an existing or newly resolved entity."""

    id: uuid.UUID
    name: str
    entity_type: str  # character, location, event, world_rule
    aliases: list[str] = field(default_factory=list)


class EntityResolver:
    """In-memory and project-scoped entity resolution registry.

    Maps note filenames, clean targets, and character aliases to stable UUIDs,
    ensuring duplicate entities are never created on re-index.
    """

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        # Normalized name (lowercase) -> ResolvedEntity
        self._registry_by_name: dict[str, ResolvedEntity] = {}
        # Entity UUID -> ResolvedEntity
        self._registry_by_id: dict[uuid.UUID, ResolvedEntity] = {}

    @staticmethod
    def normalize_name(name: str) -> str:
        """Strip file path, extension, wikilink syntax, and lowercase."""
        clean = clean_link_target(name)
        # Strip directory path and extension if present
        clean = Path(clean).stem
        return clean.strip().lower()

    def register(
        self,
        entity_id: uuid.UUID,
        name: str,
        entity_type: str,
        aliases: list[str] | None = None,
    ) -> ResolvedEntity:
        """Register an entity and all its alias variants in the lookup tables."""
        aliases = aliases or []
        resolved = ResolvedEntity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            aliases=aliases,
        )
        self._registry_by_id[entity_id] = resolved

        # Register primary name
        norm_primary = self.normalize_name(name)
        self._registry_by_name[norm_primary] = resolved

        # Register aliases
        for alias in aliases:
            norm_alias = self.normalize_name(alias)
            if norm_alias:
                self._registry_by_name[norm_alias] = resolved

        return resolved

    def resolve(self, reference: str) -> ResolvedEntity | None:
        """Resolve a name, wikilink, or alias to a registered entity."""
        norm = self.normalize_name(reference)
        return self._registry_by_name.get(norm)

    def get_or_create_id(
        self,
        name: str,
        entity_type: str,
        aliases: list[str] | None = None,
        forced_id: uuid.UUID | None = None,
    ) -> tuple[uuid.UUID, bool]:
        """Resolve an existing entity ID or generate a new stable UUID.

        Returns (entity_id, is_new).
        """
        existing = self.resolve(name)
        if existing:
            # If aliases were provided, add any newly discovered aliases
            if aliases:
                for alias in aliases:
                    norm_alias = self.normalize_name(alias)
                    if norm_alias and norm_alias not in self._registry_by_name:
                        self._registry_by_name[norm_alias] = existing
                        existing.aliases.append(alias)
            return existing.id, False

        new_id = forced_id or uuid.uuid4()
        self.register(new_id, name, entity_type, aliases)
        return new_id, True
