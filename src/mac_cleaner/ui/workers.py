from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from mac_cleaner.domain.models import (
    AppInfo,
    Category,
    CleanupPlan,
    Confidence,
    MatchReason,
    RelatedItem,
)
from mac_cleaner.domain.sizes import path_size
from mac_cleaner.services.deletion_service import DeletionResult, DeletionService
from mac_cleaner.services.scan_service import ScanService


class AppsScanWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(
        self, service: ScanService, *, compute_size: bool = False, parent=None
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.compute_size = compute_size

    def run(self) -> None:
        try:
            self.service.refresh()
            apps = self.service.list_apps(compute_size=self.compute_size)
            self.finished_ok.emit(apps)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RelatedScanWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, service: ScanService, app: AppInfo, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.app = app

    def run(self) -> None:
        try:
            items = self.service.related_for_app(self.app, compute_size=True)
            self.finished_ok.emit(items)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class OrphansScanWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, service: ScanService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

    def run(self) -> None:
        try:
            self.service.refresh()
            self.finished_ok.emit(self.service.orphans(compute_size=True))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class JunkScanWorker(QThread):
    """Returns RelatedItem rows (sized) grouped later by note/title."""

    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, service: ScanService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

    def run(self) -> None:
        try:
            self.service.refresh()
            categories = self.service.junk(compute_size=False)
            items: list[RelatedItem] = []
            cache = self.service.session.size_cache
            for cat in categories:
                category = Category.LOGS if cat.id == "user_logs" else Category.CACHE
                for path in sorted(cat.paths, key=lambda p: p.name.lower()):
                    if not path.exists():
                        continue
                    cached = cache.get(path)
                    size = cached if cached is not None else path_size(path, cache=cache)
                    items.append(
                        RelatedItem(
                            path=path,
                            category=category,
                            reason=MatchReason.JUNK,
                            confidence=Confidence.MEDIUM,
                            risk=cat.risk,
                            size_bytes=size,
                            selected=False,
                            note=cat.title,
                        )
                    )
            items.sort(key=lambda i: (i.note, -i.size_bytes, str(i.path)))
            self.finished_ok.emit(items)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeleteWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(
        self, service: DeletionService, plan: CleanupPlan, parent=None
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.plan = plan

    def run(self) -> None:
        try:
            result: DeletionResult = self.service.execute(self.plan, dry_run=False)
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
