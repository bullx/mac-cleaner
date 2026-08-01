from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mac_cleaner.domain.models import AppInfo, CleanupPlan, RelatedItem
from mac_cleaner.domain.sizes import format_bytes
from mac_cleaner.infra.macos import (
    can_list_containers,
    is_app_running,
    open_full_disk_access_settings,
    quit_app,
    reveal_in_finder,
)
from mac_cleaner.services.deletion_service import DeletionService
from mac_cleaner.services.plan_service import PlanService
from mac_cleaner.services.scan_service import ScanService
from mac_cleaner.services.scan_session import ScanSession
from mac_cleaner.ui.theme import APP_QSS
from mac_cleaner.ui.widgets.checkable_tree import CheckableTree
from mac_cleaner.ui.widgets.confirm_dialog import ConfirmDialog
from mac_cleaner.ui.workers import (
    AppsScanWorker,
    DeleteWorker,
    JunkScanWorker,
    OrphansScanWorker,
    RelatedScanWorker,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AppUnload")
        self.resize(1200, 780)
        self.setMinimumSize(980, 660)

        self.session = ScanSession()
        self.scan = ScanService(self.session)
        self.plans = PlanService()
        self.deletion = DeletionService(self.plans)

        self._apps: list[AppInfo] = []
        self._related: list[RelatedItem] = []
        self._orphans: list[RelatedItem] = []
        self._junk_items: list[RelatedItem] = []
        self._current_app: AppInfo | None = None
        self._related_token = 0
        self._threads: list = []
        self._scan_busy = False

        root = QWidget()
        root.setObjectName("centralRoot")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        outer.addLayout(self._build_header())
        self.banner = self._build_banner()
        outer.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_apps_tab(), "Apps")
        self.tabs.addTab(self._build_orphans_tab(), "Orphans")
        self.tabs.addTab(self._build_junk_tab(), "Junk")
        outer.addWidget(self.tabs, stretch=1)

        self.status = QLabel("Ready")
        self.status.setObjectName("muted")
        outer.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        outer.addWidget(self.progress)

        self.setStyleSheet(APP_QSS)
        self._refresh_fda_banner()
        self.reload_apps()

    # --- chrome ----------------------------------------------------------
    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        titles = QVBoxLayout()
        brand = QLabel("AppUnload")
        brand.setObjectName("brand")
        tag = QLabel(
            "Uninstall apps and clear hard-to-find leftovers — review, then Trash."
        )
        tag.setObjectName("tagline")
        titles.addWidget(brand)
        titles.addWidget(tag)
        row.addLayout(titles, stretch=1)
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setObjectName("secondary")
        self.rescan_btn.setToolTip(
            "Re-scan the current tab from disk (does not delete anything)."
        )
        self.rescan_btn.clicked.connect(self._on_rescan_clicked)
        row.addWidget(self.rescan_btn, alignment=Qt.AlignmentFlag.AlignTop)
        return row

    def _build_banner(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("banner")
        layout = QHBoxLayout(frame)
        self.banner_label = QLabel()
        self.banner_label.setWordWrap(True)
        layout.addWidget(self.banner_label, stretch=1)
        btn = QPushButton("Open Full Disk Access")
        btn.setObjectName("secondary")
        btn.clicked.connect(open_full_disk_access_settings)
        layout.addWidget(btn)
        return frame

    def _refresh_fda_banner(self) -> None:
        if can_list_containers():
            self.banner.hide()
        else:
            self.banner_label.setText(
                "Full Disk Access looks limited — Containers and some Library paths "
                "may be incomplete. Grant access for thorough scans."
            )
            self.banner.show()

    # --- Apps ------------------------------------------------------------
    def _build_apps_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 8, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search apps by name…")
        self.search.textChanged.connect(self._filter_apps)
        left_l.addWidget(self.search)
        self.app_list = QListWidget()
        self.app_list.setIconSize(QSize(36, 36))
        self.app_list.setSpacing(2)
        self.app_list.currentItemChanged.connect(self._on_app_selected)
        left_l.addWidget(self.app_list, stretch=1)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(8, 0, 0, 0)

        card = QFrame()
        card.setObjectName("detailCard")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(14, 12, 14, 12)
        card_l.setSpacing(4)

        head = QHBoxLayout()
        self.detail_title = QLabel("Select an app")
        self.detail_title.setObjectName("sectionTitle")
        head.addWidget(self.detail_title, stretch=1)
        self.reclaim_label = QLabel("")
        self.reclaim_label.setObjectName("reclaim")
        head.addWidget(self.reclaim_label)
        card_l.addLayout(head)

        self.detail_meta = QLabel(
            "Pick an app on the left to find leftovers under ~/Library and related folders."
        )
        self.detail_meta.setObjectName("muted")
        self.detail_meta.setWordWrap(True)
        card_l.addWidget(self.detail_meta)
        right_l.addWidget(card)

        self.path_search = QLineEdit()
        self.path_search.setPlaceholderText("Filter related paths…")
        self.path_search.textChanged.connect(
            lambda t: self.related_tree.apply_filter(t)
        )
        right_l.addWidget(self.path_search)

        self.related_tree = CheckableTree()
        self.related_tree.selection_changed.connect(self._update_related_totals)
        self.related_tree.reveal_requested.connect(self._reveal)
        right_l.addWidget(self.related_tree, stretch=1)

        self.related_summary = QLabel("0 selected · 0 B")
        self.related_summary.setObjectName("summaryBar")
        right_l.addWidget(self.related_summary)

        actions = QHBoxLayout()
        safe_btn = QPushButton("Select safe")
        safe_btn.setObjectName("secondary")
        safe_btn.clicked.connect(self.related_tree.select_safe)
        actions.addWidget(safe_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.related_tree.clear_selection_checks)
        actions.addWidget(clear_btn)
        actions.addStretch(1)
        self.uninstall_btn = QPushButton("Move selected to Trash")
        self.uninstall_btn.setObjectName("danger")
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.clicked.connect(self._uninstall_current_app)
        actions.addWidget(self.uninstall_btn)
        right_l.addLayout(actions)

        splitter.addWidget(right)
        splitter.setSizes([300, 860])
        layout.addWidget(splitter)
        return page

    # --- Orphans ---------------------------------------------------------
    def _build_orphans_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Leftovers with no matching installed app")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        hint = QLabel(
            "Check a category to select every path inside it. "
            "Right-click a path to reveal it in Finder."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.orphan_search = QLineEdit()
        self.orphan_search.setPlaceholderText("Filter orphan paths…")
        self.orphan_search.textChanged.connect(
            lambda t: self.orphan_tree.apply_filter(t)
        )
        layout.addWidget(self.orphan_search)

        self.orphan_tree = CheckableTree()
        self.orphan_tree.selection_changed.connect(self._update_orphan_totals)
        self.orphan_tree.reveal_requested.connect(self._reveal)
        layout.addWidget(self.orphan_tree, stretch=1)

        self.orphan_summary = QLabel("0 selected · 0 B")
        self.orphan_summary.setObjectName("summaryBar")
        layout.addWidget(self.orphan_summary)

        row = QHBoxLayout()
        scan_btn = QPushButton("Scan orphans")
        scan_btn.setObjectName("secondary")
        scan_btn.clicked.connect(self.reload_orphans)
        row.addWidget(scan_btn)
        self.orphan_reclaim = QLabel("")
        self.orphan_reclaim.setObjectName("reclaim")
        row.addWidget(self.orphan_reclaim)
        row.addStretch(1)
        self.orphan_btn = QPushButton("Move selected to Trash")
        self.orphan_btn.setObjectName("danger")
        self.orphan_btn.setEnabled(False)
        self.orphan_btn.clicked.connect(self._trash_orphans)
        row.addWidget(self.orphan_btn)
        layout.addLayout(row)
        return page

    # --- Junk ------------------------------------------------------------
    def _build_junk_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Regenerable junk")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        hint = QLabel(
            "Conservative categories only. Check a category to select all paths inside. "
            "Apple system caches are excluded."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.junk_search = QLineEdit()
        self.junk_search.setPlaceholderText("Filter junk paths…")
        self.junk_search.textChanged.connect(lambda t: self.junk_tree.apply_filter(t))
        layout.addWidget(self.junk_search)

        self.junk_tree = CheckableTree()
        self.junk_tree.selection_changed.connect(self._update_junk_totals)
        self.junk_tree.reveal_requested.connect(self._reveal)
        layout.addWidget(self.junk_tree, stretch=1)

        self.junk_summary = QLabel("0 selected · 0 B")
        self.junk_summary.setObjectName("summaryBar")
        layout.addWidget(self.junk_summary)

        row = QHBoxLayout()
        scan_btn = QPushButton("Scan junk")
        scan_btn.setObjectName("secondary")
        scan_btn.clicked.connect(self.reload_junk)
        row.addWidget(scan_btn)
        self.junk_reclaim = QLabel("")
        self.junk_reclaim.setObjectName("reclaim")
        row.addWidget(self.junk_reclaim)
        row.addStretch(1)
        self.junk_btn = QPushButton("Move selected to Trash")
        self.junk_btn.setObjectName("danger")
        self.junk_btn.setEnabled(False)
        self.junk_btn.clicked.connect(self._trash_junk)
        row.addWidget(self.junk_btn)
        layout.addLayout(row)
        return page

    # --- helpers ---------------------------------------------------------
    def _reveal(self, item: RelatedItem) -> None:
        reveal_in_finder(item.path)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._scan_busy = busy
        self.progress.setVisible(busy)
        self.rescan_btn.setEnabled(not busy)
        if message:
            self.status.setText(message)

    def _track(self, thread) -> None:
        self._threads.append(thread)

        def _cleanup() -> None:
            if thread in self._threads:
                self._threads.remove(thread)
            thread.deleteLater()

        thread.finished.connect(_cleanup)

    def _on_rescan_clicked(self) -> None:
        # Rescan = refresh discovery only; Trash buttons perform deletes.
        if self._scan_busy:
            return
        self.session.invalidate()
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.related_tree.clear()
            self.related_summary.setText("Rescanning leftovers…")
            self.reclaim_label.setText("")
            self.uninstall_btn.setEnabled(False)
            self.reload_apps()
        elif idx == 1:
            self.orphan_tree.clear()
            self.orphan_summary.setText("Rescanning…")
            self.reload_orphans()
        else:
            self.junk_tree.clear()
            self.junk_summary.setText("Rescanning…")
            self.reload_junk()

    # --- Apps data -------------------------------------------------------
    def reload_apps(self) -> None:
        self._set_busy(True, "Scanning installed apps…")
        worker = AppsScanWorker(self.scan, compute_size=True, parent=self)
        worker.finished_ok.connect(self._on_apps_loaded)
        worker.failed.connect(self._on_failed)
        self._track(worker)
        worker.start()

    def _on_apps_loaded(self, apps: list) -> None:
        self._apps = apps
        self._filter_apps(self.search.text())
        self._refresh_fda_banner()
        # Selection restore uses blockSignals, so leftovers would stay stale
        # unless we explicitly re-scan the selected app after a full apps reload.
        selected = self._current_app
        if selected is not None:
            match = next((a for a in apps if a.path == selected.path), None)
            if match is not None:
                self._current_app = match
                self._start_related_scan(match)
                return
            self._current_app = None
            self.detail_title.setText("Select an app")
            self.detail_meta.setText(
                "Pick an app on the left to find leftovers under ~/Library and related folders."
            )
            self.related_tree.clear()
            self.related_summary.setText("0 selected · 0 B")
            self.reclaim_label.setText("")
            self.uninstall_btn.setEnabled(False)
        self._set_busy(False, f"Found {len(apps)} apps")

    def _filter_apps(self, text: str) -> None:
        current_path = None
        cur = self.app_list.currentItem()
        if cur:
            app = cur.data(Qt.ItemDataRole.UserRole)
            if isinstance(app, AppInfo):
                current_path = app.path

        self.app_list.blockSignals(True)
        self.app_list.clear()
        q = text.strip().lower()
        restore = None
        for app in self._apps:
            if app.protected:
                continue
            if q and q not in f"{app.name} {app.bundle_id}".lower():
                continue

            # Name + size only — never show reverse-DNS as the main label.
            subtitle = format_bytes(app.size_bytes) if app.size_bytes else (
                f"v{app.version}" if app.version else "Installed app"
            )
            item = QListWidgetItem(f"{app.name}\n{subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, app)
            item.setToolTip(
                f"{app.name}\n{app.bundle_id or '—'}\n{app.path}\n"
                f"Version {app.version or '?'}"
            )
            item.setSizeHint(QSize(10, 54))
            if app.icon_path and app.icon_path.exists():
                pix = QPixmap(str(app.icon_path))
                if not pix.isNull():
                    item.setIcon(
                        QIcon(
                            pix.scaled(
                                36,
                                36,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    )
            self.app_list.addItem(item)
            if current_path and app.path == current_path:
                restore = item

        if restore:
            self.app_list.setCurrentItem(restore)
        self.app_list.blockSignals(False)

    def _on_app_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        app = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(app, AppInfo):
            return
        self._start_related_scan(app)

    def _start_related_scan(self, app: AppInfo) -> None:
        self._current_app = app
        self._related_token += 1
        token = self._related_token
        self.detail_title.setText(app.name)
        self.detail_meta.setText(
            f"Version {app.version or '?'}  ·  {format_bytes(app.size_bytes) if app.size_bytes else 'size pending'}\n"
            f"{app.path}"
        )
        self.related_tree.clear()
        self.path_search.clear()
        self.reclaim_label.setText("")
        self.related_summary.setText("Scanning leftovers…")
        self.uninstall_btn.setEnabled(False)
        self._set_busy(True, f"Finding leftovers for {app.name}…")
        worker = RelatedScanWorker(self.scan, app, parent=self)
        worker.finished_ok.connect(lambda items, t=token: self._on_related_loaded(items, t))
        worker.failed.connect(self._on_failed)
        self._track(worker)
        worker.start()

    def _on_related_loaded(self, items: list, token: int) -> None:
        if token != self._related_token:
            return
        self._related = items
        if self._current_app:
            app = self._current_app
            app.related_bytes = sum(i.size_bytes for i in items if not i.locked)
            app_size = (
                format_bytes(app.size_bytes) if app.size_bytes else "—"
            )
            reclaim = format_bytes(app.related_bytes)
            self.detail_meta.setText(
                f"Version {app.version or '?'}  ·  App {app_size}  ·  "
                f"Leftovers {reclaim}\n"
                f"{app.path}\n"
                f"Bundle: {app.bundle_id or '—'}"
            )
        self.related_tree.populate(items)
        self.related_tree.apply_filter(self.path_search.text())
        self._update_related_totals()
        self._set_busy(False, f"{len(items)} related path(s)")

    def _update_related_totals(self) -> None:
        count, total = self.related_tree.selected_bytes(self._related)
        self.reclaim_label.setText(format_bytes(total) if count else "")
        self.related_summary.setText(f"{count} selected · {format_bytes(total)}")
        self.uninstall_btn.setEnabled(count > 0)

    def _ensure_app_quit(self, app: AppInfo) -> bool:
        if not is_app_running(app.path, app.bundle_id):
            return True
        answer = QMessageBox.question(
            self,
            "App is running",
            f"{app.name} appears to be running. Quit it before cleaning?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Yes and not quit_app(app.name):
            QMessageBox.warning(
                self,
                "Could not quit",
                f"Couldn't quit {app.name}. Quit it manually, then try again.",
            )
            return False
        return True

    def _uninstall_current_app(self) -> None:
        if not self._current_app:
            return
        if not self._ensure_app_quit(self._current_app):
            return
        plan = self.plans.build_from_related(
            self._related, label=f"Uninstall {self._current_app.name}"
        )
        safe, errors = self.plans.validate(plan)
        if errors:
            self.status.setText(f"Skipped {len(errors)} unsafe path(s)")
        if not safe.items:
            QMessageBox.information(self, "Nothing to delete", "No valid selected paths.")
            return
        if ConfirmDialog(safe, self).exec() != ConfirmDialog.DialogCode.Accepted:
            return
        self._run_delete(safe)

    # --- Orphans data ----------------------------------------------------
    def reload_orphans(self) -> None:
        self._set_busy(True, "Scanning orphan leftovers…")
        worker = OrphansScanWorker(self.scan, parent=self)
        worker.finished_ok.connect(self._on_orphans_loaded)
        worker.failed.connect(self._on_failed)
        self._track(worker)
        worker.start()

    def _on_orphans_loaded(self, items: list) -> None:
        self._orphans = items
        self.orphan_tree.populate(items)
        self.orphan_search.clear()
        self._update_orphan_totals()
        self._set_busy(False, f"Rescan complete · {len(items)} orphan path(s)")

    def _update_orphan_totals(self) -> None:
        count, total = self.orphan_tree.selected_bytes(self._orphans)
        self.orphan_reclaim.setText(format_bytes(total) if count else "")
        self.orphan_summary.setText(f"{count} selected · {format_bytes(total)}")
        self.orphan_btn.setEnabled(count > 0)

    def _trash_orphans(self) -> None:
        plan = self.plans.build_from_related(self._orphans, label="Orphan cleanup")
        safe, _ = self.plans.validate(plan)
        if not safe.items:
            return
        if ConfirmDialog(safe, self).exec() != ConfirmDialog.DialogCode.Accepted:
            return
        self._run_delete(safe)

    # --- Junk data -------------------------------------------------------
    def reload_junk(self) -> None:
        self._set_busy(True, "Scanning junk…")
        worker = JunkScanWorker(self.scan, parent=self)
        worker.finished_ok.connect(self._on_junk_loaded)
        worker.failed.connect(self._on_failed)
        self._track(worker)
        worker.start()

    def _on_junk_loaded(self, items: list) -> None:
        self._junk_items = items
        self.junk_tree.populate(items, group_key=lambda i: i.note or "Junk")
        self.junk_search.clear()
        self._update_junk_totals()
        groups = {i.note for i in items}
        self._set_busy(
            False,
            f"Rescan complete · {len(groups)} junk categor(ies) · {len(items)} path(s)",
        )

    def _update_junk_totals(self) -> None:
        count, total = self.junk_tree.selected_bytes(self._junk_items)
        self.junk_reclaim.setText(format_bytes(total) if count else "")
        self.junk_summary.setText(f"{count} selected · {format_bytes(total)}")
        self.junk_btn.setEnabled(count > 0)

    def _trash_junk(self) -> None:
        plan = self.plans.build_from_related(self._junk_items, label="Junk cleanup")
        safe, _ = self.plans.validate(plan)
        if not safe.items:
            QMessageBox.information(
                self, "Nothing to delete", "No valid selected junk paths."
            )
            return
        if ConfirmDialog(safe, self).exec() != ConfirmDialog.DialogCode.Accepted:
            return
        self._run_delete(safe)

    # --- Delete ----------------------------------------------------------
    def _run_delete(self, plan: CleanupPlan) -> None:
        self._set_busy(True, f"Moving {len(plan.items)} item(s) to Trash…")
        worker = DeleteWorker(self.deletion, plan, parent=self)
        worker.finished_ok.connect(self._on_delete_finished)
        worker.failed.connect(self._on_failed)
        self._track(worker)
        worker.start()

    def _on_delete_finished(self, result) -> None:
        self._set_busy(
            False, f"Trashed {len(result.trashed)}; failed {len(result.failed)}"
        )
        msg = f"Moved {len(result.trashed)} item(s) to Trash."
        if result.manifest:
            msg += f"\nLog: {result.manifest}"
        if result.failed:
            preview = "\n".join(f"{p}: {err}" for p, err in result.failed[:8])
            msg += f"\n\nSome paths failed:\n{preview}"
        QMessageBox.information(self, "Cleanup finished", msg)
        self.session.invalidate()
        self.reload_apps()
        self.related_tree.clear()
        self._related = []
        if self.tabs.currentIndex() == 1:
            self.reload_orphans()
        if self.tabs.currentIndex() == 2:
            self.reload_junk()

    def _on_failed(self, message: str) -> None:
        self._set_busy(False, "Error")
        QMessageBox.critical(self, "Operation failed", message)

    def closeEvent(self, event) -> None:  # noqa: N802
        for thread in list(self._threads):
            if thread.isRunning():
                thread.requestInterruption()
                if not thread.wait(3000):
                    thread.terminate()
                    thread.wait(500)
        self._threads.clear()
        super().closeEvent(event)
