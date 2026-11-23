"""Obsidian [[WikiLink]] extraction and normalization utilities."""

import re
from dataclasses import dataclass

# Regex matching !?[[Target(#Anchor)?(|Alias)?]]
WIKILINK_REGEX = re.compile(
    r"(?P<embed>!)?\[\[(?P<target>[^#|\]]+)(?:#(?P<anchor>[^|\]]+))?(?:\|(?P<alias>[^\]]+))?\]\]"
)


@dataclass(frozen=True)
class WikiLink:
    """Represents a parsed Obsidian wikilink."""

    raw: str
    target: str
    alias: str | None = None
    anchor: str | None = None
    is_embed: bool = False

    @property
    def display_name(self) -> str:
        """Returns the visible label of the link in rendered text."""
        return self.alias if self.alias is not None else self.target


def extract_wikilinks(text: str) -> list[WikiLink]:
    """Extract all Obsidian wikilinks from text preserving anchors and aliases."""
    if not text:
        return []

    links: list[WikiLink] = []
    for match in WIKILINK_REGEX.finditer(text):
        embed_flag = match.group("embed") is not None
        target = match.group("target").strip()
        anchor = match.group("anchor").strip() if match.group("anchor") else None
        alias = match.group("alias").strip() if match.group("alias") else None

        links.append(
            WikiLink(
                raw=match.group(0),
                target=target,
                alias=alias,
                anchor=anchor,
                is_embed=embed_flag,
            )
        )
    return links


def clean_link_target(raw_target: str) -> str:
    """Extract clean target note name from a link string or wikilink."""
    if "[[" in raw_target:
        links = extract_wikilinks(raw_target)
        if links:
            return links[0].target
    return raw_target.strip("[]\"' ")
