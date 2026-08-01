from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Category(str, Enum):
    APP = "App"
    SUPPORT = "Support"
    CACHE = "Cache"
    PREFERENCES = "Preferences"
    CONTAINERS = "Containers"
    GROUP_CONTAINERS = "Group Containers"
    AGENTS = "Agents"
    LOGS = "Logs"
    STATE = "State"
    OTHER = "Other"
    PROFILE = "Profile"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchReason(str, Enum):
    EXACT_BUNDLE = "exact_bundle"
    BUNDLE_PREFIX = "bundle_prefix"
    NAME_MATCH = "name_match"
    PROFILE = "profile"
    SHARED_CAUTION = "shared_caution"
    ORPHAN = "orphan"
    JUNK = "junk"


class Risk(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    LOCKED = "locked"


@dataclass(slots=True)
class AppInfo:
    name: str
    path: Path
    bundle_id: str
    version: str = ""
    icon_path: Path | None = None
    size_bytes: int = 0
    related_bytes: int = 0  # cached reclaimable from last related scan
    protected: bool = False

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def sort_bytes(self) -> int:
        return self.related_bytes or self.size_bytes


@dataclass(slots=True)
class RelatedItem:
    path: Path
    category: Category
    reason: MatchReason
    confidence: Confidence
    risk: Risk = Risk.SAFE
    size_bytes: int = 0
    size_pending: bool = False
    selected: bool = False
    note: str = ""
    locked: bool = False

    @property
    def exists(self) -> bool:
        return self.path.exists()


@dataclass
class CleanupPlan:
    items: list[RelatedItem] = field(default_factory=list)
    label: str = ""

    @property
    def selected_items(self) -> list[RelatedItem]:
        return [i for i in self.items if i.selected and not i.locked]

    @property
    def total_selected_bytes(self) -> int:
        return sum(i.size_bytes for i in self.selected_items)

    @property
    def total_bytes(self) -> int:
        return sum(i.size_bytes for i in self.items)


@dataclass(slots=True)
class JunkCategory:
    id: str
    title: str
    description: str
    paths: list[Path]
    size_bytes: int = 0
    selected: bool = False
    risk: Risk = Risk.SAFE
