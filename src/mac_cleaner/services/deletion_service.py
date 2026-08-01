from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mac_cleaner.domain.models import CleanupPlan
from mac_cleaner.domain.rules import is_path_allowed_for_trash
from mac_cleaner.infra.trash import move_to_trash, write_deletion_manifest
from mac_cleaner.services.plan_service import PlanService


@dataclass
class DeletionResult:
    trashed: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    manifest: Path | None = None
    dry_run: bool = False


class DeletionService:
    def __init__(self, plan_service: PlanService | None = None) -> None:
        self.plans = plan_service or PlanService()

    def execute(self, plan: CleanupPlan, *, dry_run: bool = False) -> DeletionResult:
        safe_plan, pre_errors = self.plans.validate(plan)
        result = DeletionResult(dry_run=dry_run)
        for msg in pre_errors:
            # Recover path from message prefix
            path_str = msg.split(":", 1)[0]
            result.failed.append((Path(path_str), msg.split(":", 1)[-1].strip()))

        paths = [i.path for i in safe_plan.items]
        if dry_run:
            result.trashed = paths
            return result

        for path in paths:
            allowed, reason = is_path_allowed_for_trash(path)
            if not allowed:
                result.failed.append((path, reason))
                continue
            if not path.exists():
                result.failed.append((path, "already gone"))
                continue
            try:
                move_to_trash(path)
                result.trashed.append(path)
            except Exception as exc:  # noqa: BLE001 — surface per-path errors to UI
                result.failed.append((path, str(exc)))

        if result.trashed:
            try:
                result.manifest = write_deletion_manifest(
                    result.trashed, label=safe_plan.label
                )
            except OSError:
                result.manifest = None
        return result
