from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import CleanupPlan, JunkCategory, RelatedItem
from mac_cleaner.domain.rules import is_path_allowed_for_trash


class PlanService:
    def build_from_related(
        self, items: list[RelatedItem], *, label: str = ""
    ) -> CleanupPlan:
        selected = [i for i in items if i.selected and not i.locked]
        plan = CleanupPlan(items=list(selected), label=label)
        return plan

    def build_from_junk(self, categories: list[JunkCategory]) -> CleanupPlan:
        items: list[RelatedItem] = []
        from mac_cleaner.domain.models import (
            Category,
            Confidence,
            MatchReason,
            Risk,
        )
        from mac_cleaner.domain.sizes import path_size

        for cat in categories:
            if not cat.selected:
                continue
            for path in cat.paths:
                if not path.exists():
                    continue
                items.append(
                    RelatedItem(
                        path=path,
                        category=Category.CACHE if cat.id != "user_logs" else Category.LOGS,
                        reason=MatchReason.JUNK,
                        confidence=Confidence.MEDIUM,
                        risk=cat.risk,
                        size_bytes=path_size(path),
                        selected=True,
                        note=cat.title,
                    )
                )
        return CleanupPlan(items=items, label="Junk cleanup")

    def validate(self, plan: CleanupPlan) -> tuple[CleanupPlan, list[str]]:
        """Filter out illegal paths; return (safe_plan, errors)."""
        ok_items: list[RelatedItem] = []
        errors: list[str] = []
        for item in plan.items:
            allowed, reason = is_path_allowed_for_trash(item.path)
            if not allowed:
                errors.append(f"{item.path}: {reason}")
                continue
            if item.locked:
                errors.append(f"{item.path}: locked")
                continue
            ok_items.append(item)
        return CleanupPlan(items=ok_items, label=plan.label), errors

    def paths(self, plan: CleanupPlan) -> list[Path]:
        return [i.path for i in plan.items]
