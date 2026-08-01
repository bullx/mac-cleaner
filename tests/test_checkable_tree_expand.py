"""Mock UI tests for parent ▶/▼ expand + indented children.

These run with a real QApplication (offscreen when possible) and drive
clicks through the same mousePressEvent path the user uses.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from mac_cleaner.domain.models import (
    Category,
    Confidence,
    MatchReason,
    RelatedItem,
    Risk,
)
from mac_cleaner.ui.widgets.checkable_tree import (
    COL_EXPAND,
    COL_NAME,
    CheckableTree,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def _items_for_groups(groups: dict[str, int]) -> list[RelatedItem]:
    out: list[RelatedItem] = []
    for note, count in groups.items():
        for i in range(count):
            out.append(
                RelatedItem(
                    path=Path(f"/tmp/{note}/file-{i}.cache"),
                    category=Category.CACHE,
                    reason=MatchReason.ORPHAN,
                    confidence=Confidence.HIGH,
                    risk=Risk.SAFE,
                    size_bytes=1000 * (i + 1),
                    selected=False,
                    note=note,
                )
            )
    return out


def _click_expand(tree: CheckableTree, group) -> None:
    """Single-click the center of the expand column cell for a group."""
    tree.scrollToItem(group)
    QApplication.processEvents()
    rect = tree.visualItemRect(group)
    # Center of the dedicated expand column (column 0).
    x = tree.columnViewportPosition(COL_EXPAND) + tree.columnWidth(COL_EXPAND) // 2
    y = rect.center().y()
    pos = QPoint(x, y)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(pos),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tree.mousePressEvent(press)
    QApplication.processEvents()


def test_all_parents_expand_and_collapse_on_arrow_click(qapp):
    tree = CheckableTree()
    tree.resize(800, 500)
    tree.show()
    QApplication.processEvents()

    groups = {"Support": 3, "Cache": 2, "Preferences": 4, "Containers": 1}
    tree.populate(_items_for_groups(groups), group_key=lambda i: i.note)
    QApplication.processEvents()

    assert tree.topLevelItemCount() == len(groups)

    for i in range(tree.topLevelItemCount()):
        group = tree.topLevelItem(i)
        assert group is not None
        assert group.text(COL_EXPAND) == "▶"
        assert group.isExpanded() is False
        assert group.childCount() >= 1

        _click_expand(tree, group)
        assert group.isExpanded() is True, f"failed to expand {group.text(COL_NAME)}"
        assert group.text(COL_EXPAND) == "▼"

        _click_expand(tree, group)
        assert group.isExpanded() is False, f"failed to collapse {group.text(COL_NAME)}"
        assert group.text(COL_EXPAND) == "▶"


def test_children_are_indented_right_of_parent(qapp):
    tree = CheckableTree()
    tree.resize(800, 500)
    tree.show()
    QApplication.processEvents()

    tree.populate(
        _items_for_groups({"Cache": 2}),
        group_key=lambda i: i.note,
    )
    group = tree.topLevelItem(0)
    assert group is not None
    group.setExpanded(True)
    QApplication.processEvents()

    child = group.child(0)
    assert child is not None
    parent_left = tree.visualItemRect(group).left()
    child_left = tree.visualItemRect(child).left()
    assert child_left > parent_left
    # Name column content for children should also sit further right.
    parent_name_x = tree.visualItemRect(group).left() + tree.columnWidth(COL_EXPAND)
    # Child row starts indented; name follows after expand gutter.
    assert child_left >= parent_left + tree.indentation() // 2


def test_expand_click_does_not_toggle_checkbox(qapp):
    tree = CheckableTree()
    tree.resize(800, 500)
    tree.show()
    QApplication.processEvents()

    tree.populate(_items_for_groups({"Logs": 2}), group_key=lambda i: i.note)
    group = tree.topLevelItem(0)
    assert group is not None
    before = group.checkState(COL_NAME)
    _click_expand(tree, group)
    assert group.isExpanded() is True
    assert group.checkState(COL_NAME) == before


def test_parent_checkbox_still_selects_children(qapp):
    tree = CheckableTree()
    tree.resize(800, 500)
    tree.show()
    QApplication.processEvents()

    items = _items_for_groups({"Agents": 3})
    tree.populate(items, group_key=lambda i: i.note)
    group = tree.topLevelItem(0)
    assert group is not None
    group.setExpanded(True)
    QApplication.processEvents()

    group.setCheckState(COL_NAME, Qt.CheckState.Checked)
    QApplication.processEvents()
    assert all(i.selected for i in items)
