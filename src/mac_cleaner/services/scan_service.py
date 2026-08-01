from __future__ import annotations

from mac_cleaner.domain.models import AppInfo, JunkCategory, RelatedItem
from mac_cleaner.scanners.apps import scan_installed_apps
from mac_cleaner.scanners.junk import scan_junk
from mac_cleaner.scanners.orphans import scan_orphans
from mac_cleaner.scanners.related import find_related_files
from mac_cleaner.services.scan_session import ScanSession


class ScanService:
    def __init__(self, session: ScanSession | None = None) -> None:
        self.session = session or ScanSession()

    def list_apps(self, *, compute_size: bool = False) -> list[AppInfo]:
        return scan_installed_apps(compute_size=compute_size, include_system=False)

    def related_for_app(
        self,
        app: AppInfo,
        *,
        compute_size: bool = False,
    ) -> list[RelatedItem]:
        return find_related_files(
            app,
            compute_size=compute_size,
            library_index=self.session.index,
        )

    def orphans(self, *, compute_size: bool = False) -> list[RelatedItem]:
        return scan_orphans(
            compute_size=compute_size,
            library_index=self.session.index,
        )

    def junk(self, *, compute_size: bool = False) -> list[JunkCategory]:
        return scan_junk(compute_size=compute_size)

    def refresh(self) -> None:
        self.session.invalidate()
        self.session.refresh_index()
