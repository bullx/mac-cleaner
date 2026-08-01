from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from mac_cleaner.domain.models import CleanupPlan
from mac_cleaner.domain.sizes import format_bytes


class ConfirmDialog(QDialog):
    def __init__(self, plan: CleanupPlan, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm move to Trash")
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        title = QLabel(
            f"Move {len(plan.items)} item(s) to Trash — "
            f"{format_bytes(plan.total_selected_bytes if plan.selected_items else plan.total_bytes)}"
        )
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Files go to Trash (reversible). Review the list carefully before continuing."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        listing = QListWidget()
        for item in plan.items:
            text = f"{format_bytes(item.size_bytes):>10}  {item.path}"
            listing.addItem(QListWidgetItem(text))
        layout.addWidget(listing, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok:
            ok.setText("Move to Trash")
            ok.setObjectName("danger")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
