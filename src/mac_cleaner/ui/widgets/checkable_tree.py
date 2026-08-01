from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from mac_cleaner.domain.models import RelatedItem
from mac_cleaner.domain.sizes import format_bytes

REASON_LABELS: dict[str, str] = {
    "exact_bundle": "Exact bundle match",
    "bundle_prefix": "Related bundle",
    "name_match": "Name match",
    "profile": "Known app profile",
    "shared_caution": "Shared folder — review carefully",
    "orphan": "No matching installed app",
    "junk": "Regenerable junk",
}

_TEXT = QColor("#0f172a")
_MUTED = QColor("#64748b")
_GROUP_BG = QColor("#f1f5f9")
_CAUTION = QColor("#b45309")
_SIZE = QColor("#334155")
_ARROW = QColor("#475569")

# 0 = dedicated ▶/▼ (only clickable expand control)
# 1 = checkbox + name
# 2 = size
# 3 = why
COL_EXPAND = 0
COL_NAME = 1
COL_SIZE = 2
COL_WHY = 3

_TITLE_ROLE = Qt.ItemDataRole.UserRole + 1
_CHILD_INDENT_PX = 28


def reason_label(item: RelatedItem) -> str:
    base = REASON_LABELS.get(item.reason.value, item.reason.value.replace("_", " "))
    if item.note and item.note not in base:
        return f"{base} — {item.note}"
    return base


class CheckableTree(QTreeWidget):
    """Path checklist with a reliable ▶/▼ column and indented children."""

    selection_changed = Signal()
    reveal_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("pathTree")
        self.setHeaderLabels(["", "Name", "Size", "Why"])
        self.setUniformRowHeights(True)
        self.setAnimated(False)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(True)
        # Native indent shifts the whole child row down-and-right.
        self.setIndentation(_CHILD_INDENT_PX)
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setExpandsOnDoubleClick(False)

        header = self.header()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setHighlightSections(False)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(28)
        header.setSectionResizeMode(COL_EXPAND, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_WHY, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(COL_EXPAND, 32)
        self.setColumnWidth(COL_SIZE, 100)

        self.itemChanged.connect(self._on_item_changed)
        self.itemExpanded.connect(self._on_expand_state)
        self.itemCollapsed.connect(self._on_expand_state)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._toggle_if_expand_click(
            event.position().toPoint()
        ):
            event.accept()
            return
        super().mousePressEvent(event)

    def _toggle_if_expand_click(self, pos: QPoint) -> bool:
        """Toggle expand only when the dedicated ▶/▼ column is clicked."""
        index = self.indexAt(pos)
        if not index.isValid() or index.column() != COL_EXPAND:
            return False
        item = self.itemFromIndex(index)
        if item is None or not self._is_group(item):
            return False
        item.setExpanded(not item.isExpanded())
        self._update_expand_glyph(item)
        return True

    def populate(
        self,
        items: list[RelatedItem],
        *,
        group_key: Callable[[RelatedItem], str] | None = None,
    ) -> None:
        key_fn = group_key or (lambda i: i.category.value)
        self.blockSignals(True)
        self.clear()

        groups: dict[str, QTreeWidgetItem] = {}
        for item in items:
            cat = key_fn(item)
            if cat not in groups:
                group = QTreeWidgetItem(self)
                group.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsUserTristate
                )
                group.setCheckState(COL_NAME, Qt.CheckState.Unchecked)
                # Never put a checkbox in the expand column.
                group.setData(COL_EXPAND, Qt.ItemDataRole.CheckStateRole, None)
                group.setData(COL_NAME, Qt.ItemDataRole.UserRole, {"kind": "group"})
                group.setData(COL_NAME, _TITLE_ROLE, cat)
                group.setText(COL_NAME, cat)
                font = QFont(group.font(COL_NAME))
                font.setBold(True)
                group.setFont(COL_NAME, font)
                for col in range(4):
                    group.setBackground(col, QBrush(_GROUP_BG))
                    group.setForeground(col, QBrush(_TEXT))
                group.setForeground(COL_EXPAND, QBrush(_ARROW))
                group.setTextAlignment(
                    COL_EXPAND, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                # Expand column must not be checkable — flags are per-item,
                # checkbox is drawn only for COL_NAME via setCheckState.
                groups[cat] = group

            row = QTreeWidgetItem(groups[cat])
            if item.locked:
                row.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                row.setDisabled(True)
                row.setCheckState(COL_NAME, Qt.CheckState.Unchecked)
            else:
                row.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                row.setCheckState(
                    COL_NAME,
                    Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked,
                )
            row.setText(COL_EXPAND, "")
            row.setData(COL_EXPAND, Qt.ItemDataRole.CheckStateRole, None)
            row.setText(COL_NAME, item.path.name or str(item.path))
            row.setText(COL_SIZE, format_bytes(item.size_bytes))
            row.setText(COL_WHY, reason_label(item))
            row.setTextAlignment(
                COL_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row.setToolTip(COL_NAME, str(item.path))
            row.setToolTip(COL_WHY, str(item.path))
            row.setData(COL_NAME, Qt.ItemDataRole.UserRole, item)
            row.setForeground(COL_NAME, QBrush(_TEXT))
            row.setForeground(COL_SIZE, QBrush(_SIZE))
            row.setForeground(
                COL_WHY, QBrush(_MUTED if item.risk.value != "caution" else _CAUTION)
            )
            if item.risk.value == "caution":
                row.setForeground(COL_NAME, QBrush(_CAUTION))

        for group in groups.values():
            self._refresh_group_totals(group)
            self._sync_group_check_state(group)
            group.setExpanded(False)
            self._update_expand_glyph(group)
        self.blockSignals(False)
        self.selection_changed.emit()

    def apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        for i in range(self.topLevelItemCount()):
            group = self.topLevelItem(i)
            if group is None:
                continue
            visible = 0
            for j in range(group.childCount()):
                row = group.child(j)
                item = row.data(COL_NAME, Qt.ItemDataRole.UserRole)
                if not isinstance(item, RelatedItem):
                    continue
                show = (not q) or q in f"{item.path} {item.note}".lower()
                row.setHidden(not show)
                if show:
                    visible += 1
            group.setHidden(bool(q) and visible == 0)

    def select_safe(self) -> None:
        self.blockSignals(True)
        for i in range(self.topLevelItemCount()):
            group = self.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                row = group.child(j)
                item = row.data(COL_NAME, Qt.ItemDataRole.UserRole)
                if not isinstance(item, RelatedItem) or item.locked:
                    continue
                safe = item.confidence.value == "high" and item.risk.value == "safe"
                item.selected = safe
                row.setCheckState(
                    COL_NAME,
                    Qt.CheckState.Checked if safe else Qt.CheckState.Unchecked,
                )
            self._sync_group_check_state(group)
        self.blockSignals(False)
        self.selection_changed.emit()

    def clear_selection_checks(self) -> None:
        self.blockSignals(True)
        for i in range(self.topLevelItemCount()):
            group = self.topLevelItem(i)
            if group is None:
                continue
            for j in range(group.childCount()):
                row = group.child(j)
                item = row.data(COL_NAME, Qt.ItemDataRole.UserRole)
                if isinstance(item, RelatedItem):
                    item.selected = False
                if row.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    row.setCheckState(COL_NAME, Qt.CheckState.Unchecked)
            self._sync_group_check_state(group)
        self.blockSignals(False)
        self.selection_changed.emit()

    def selected_bytes(self, items: list[RelatedItem]) -> tuple[int, int]:
        selected = [i for i in items if i.selected and not i.locked]
        return len(selected), sum(i.size_bytes for i in selected)

    def _is_group(self, item: QTreeWidgetItem) -> bool:
        data = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        return isinstance(data, dict) and data.get("kind") == "group"

    def _update_expand_glyph(self, group: QTreeWidgetItem) -> None:
        group.setText(COL_EXPAND, "▼" if group.isExpanded() else "▶")
        title = group.data(COL_NAME, _TITLE_ROLE)
        if title:
            group.setText(COL_NAME, str(title))

    def _on_expand_state(self, item: QTreeWidgetItem) -> None:
        if self._is_group(item):
            self._update_expand_glyph(item)

    def _refresh_group_totals(self, group: QTreeWidgetItem) -> None:
        total = 0
        for j in range(group.childCount()):
            data = group.child(j).data(COL_NAME, Qt.ItemDataRole.UserRole)
            if isinstance(data, RelatedItem):
                total += data.size_bytes
        title = group.data(COL_NAME, _TITLE_ROLE) or group.text(COL_NAME)
        group.setData(COL_NAME, _TITLE_ROLE, title)
        group.setText(COL_NAME, str(title))
        group.setText(COL_SIZE, format_bytes(total))
        group.setTextAlignment(
            COL_SIZE, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        group.setText(COL_WHY, f"{group.childCount()} item(s)")
        group.setForeground(COL_WHY, QBrush(_MUTED))
        self._update_expand_glyph(group)

    def _sync_group_check_state(self, group: QTreeWidgetItem) -> None:
        checked = enabled = 0
        for j in range(group.childCount()):
            child = group.child(j)
            if not (child.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                continue
            enabled += 1
            if child.checkState(COL_NAME) == Qt.CheckState.Checked:
                checked += 1
        if enabled == 0 or checked == 0:
            group.setCheckState(COL_NAME, Qt.CheckState.Unchecked)
        elif checked == enabled:
            group.setCheckState(COL_NAME, Qt.CheckState.Checked)
        else:
            group.setCheckState(COL_NAME, Qt.CheckState.PartiallyChecked)

    def _on_item_changed(self, row: QTreeWidgetItem, column: int) -> None:
        if column != COL_NAME:
            return
        self.blockSignals(True)
        data = row.data(COL_NAME, Qt.ItemDataRole.UserRole)
        state = row.checkState(COL_NAME)
        if isinstance(data, dict) and data.get("kind") == "group":
            target = (
                Qt.CheckState.Checked
                if state != Qt.CheckState.Unchecked
                else Qt.CheckState.Unchecked
            )
            if state == Qt.CheckState.PartiallyChecked:
                row.setCheckState(COL_NAME, Qt.CheckState.Checked)
                target = Qt.CheckState.Checked
            for j in range(row.childCount()):
                child = row.child(j)
                if not (child.flags() & Qt.ItemFlag.ItemIsUserCheckable) or child.isDisabled():
                    continue
                child.setCheckState(COL_NAME, target)
                leaf = child.data(COL_NAME, Qt.ItemDataRole.UserRole)
                if isinstance(leaf, RelatedItem):
                    leaf.selected = target == Qt.CheckState.Checked
        elif isinstance(data, RelatedItem):
            data.selected = state == Qt.CheckState.Checked
            parent = row.parent()
            if parent is not None:
                self._sync_group_check_state(parent)
        self.blockSignals(False)
        self.selection_changed.emit()

    def _context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None:
            return
        data = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        if not isinstance(data, RelatedItem):
            return
        menu = QMenu(self)
        reveal = menu.addAction("Reveal in Finder")
        if menu.exec(self.viewport().mapToGlobal(pos)) == reveal:
            self.reveal_requested.emit(data)
