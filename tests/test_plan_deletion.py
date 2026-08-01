from pathlib import Path

from mac_cleaner.domain.models import (
    Category,
    CleanupPlan,
    Confidence,
    MatchReason,
    RelatedItem,
    Risk,
)
from mac_cleaner.services.deletion_service import DeletionService
from mac_cleaner.services.plan_service import PlanService


def test_validate_filters_denied(tmp_path, monkeypatch):
    home = tmp_path / "Users" / "test"
    home.mkdir(parents=True)
    ssh = home / ".ssh"
    ssh.mkdir()
    good = home / "Library" / "Caches" / "com.example.app"
    good.mkdir(parents=True)

    monkeypatch.setattr("mac_cleaner.domain.rules.home", lambda: home.resolve())

    plan = CleanupPlan(
        items=[
            RelatedItem(
                path=ssh,
                category=Category.OTHER,
                reason=MatchReason.NAME_MATCH,
                confidence=Confidence.LOW,
                risk=Risk.CAUTION,
                selected=True,
            ),
            RelatedItem(
                path=good,
                category=Category.CACHE,
                reason=MatchReason.EXACT_BUNDLE,
                confidence=Confidence.HIGH,
                selected=True,
            ),
        ]
    )
    safe, errors = PlanService().validate(plan)
    assert len(safe.items) == 1
    assert safe.items[0].path == good
    assert errors


def test_dry_run_does_not_trash(tmp_path, monkeypatch):
    home = tmp_path / "Users" / "test"
    target = home / "Library" / "Caches" / "com.example.app"
    target.mkdir(parents=True)
    (target / "f").write_text("hi")
    monkeypatch.setattr("mac_cleaner.domain.rules.home", lambda: home.resolve())

    plan = CleanupPlan(
        items=[
            RelatedItem(
                path=target,
                category=Category.CACHE,
                reason=MatchReason.EXACT_BUNDLE,
                confidence=Confidence.HIGH,
                selected=True,
            )
        ],
        label="test",
    )
    result = DeletionService().execute(plan, dry_run=True)
    assert target.exists()
    assert result.dry_run
    assert result.trashed == [target]
