from __future__ import annotations

APP_QSS = """
QMainWindow, QWidget#centralRoot {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8fafc,
        stop:0.55 #f1f5f9,
        stop:1 #e8eef5
    );
    color: #0f172a;
    font-size: 13px;
}

QLabel#brand {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.4px;
    color: #0f172a;
}

QLabel#tagline, QLabel#muted {
    color: #64748b;
}

QLabel#sectionTitle {
    font-size: 18px;
    font-weight: 600;
    color: #0f172a;
}

QLabel#reclaim {
    font-size: 20px;
    font-weight: 700;
    color: #0f766e;
}

QLabel#summaryBar {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 600;
    color: #0f172a;
}

QLineEdit {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 9px 12px;
    color: #0f172a;
    selection-background-color: #bae6fd;
    selection-color: #0f172a;
}

QLineEdit:focus {
    border: 1px solid #38bdf8;
}

QPushButton {
    background: #0ea5e9;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 600;
}

QPushButton:hover { background: #0284c7; }
QPushButton:disabled {
    background: #cbd5e1;
    color: #f8fafc;
}

QPushButton#secondary {
    background: #ffffff;
    color: #0369a1;
    border: 1px solid #bae6fd;
}

QPushButton#secondary:hover {
    background: #f0f9ff;
}

QPushButton#danger {
    background: #ea580c;
    color: #ffffff;
}

QPushButton#danger:hover { background: #c2410c; }

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.82);
    top: -1px;
    padding: 8px;
}

QTabBar::tab {
    background: transparent;
    border: none;
    padding: 10px 18px;
    margin-right: 4px;
    color: #64748b;
    font-weight: 600;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
}

QTabBar::tab:hover:!selected {
    background: rgba(255, 255, 255, 0.55);
    color: #0f172a;
}

QFrame#banner {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 12px;
}

QFrame#detailCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QProgressBar {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    text-align: center;
    max-height: 10px;
}

QProgressBar::chunk {
    background: #38bdf8;
    border-radius: 6px;
}

/* —— App list —— */
QListWidget {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    outline: 0;
    padding: 4px;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 8px;
    color: #0f172a;
}

QListWidget::item:hover {
    background: #f1f5f9;
    color: #0f172a;
}

QListWidget::item:selected {
    background: #e0f2fe;
    color: #0f172a;
}

QListWidget::item:selected:active {
    background: #bae6fd;
    color: #0f172a;
}

/* —— Path trees (Apps / Orphans / Junk) —— */
QTreeWidget#pathTree {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    outline: 0;
    show-decoration-selected: 1;
    alternate-background-color: #ffffff;
}

QTreeWidget#pathTree::item {
    min-height: 32px;
    color: #0f172a;
    border: none;
}

QTreeWidget#pathTree::item:hover {
    background: #f8fafc;
    color: #0f172a;
}

QTreeWidget#pathTree::item:selected {
    background: #e0f2fe;
    color: #0f172a;
}

QTreeWidget#pathTree::item:selected:active {
    background: #bae6fd;
    color: #0f172a;
}

QTreeWidget#pathTree::item:selected:!active {
    background: #e0f2fe;
    color: #0f172a;
}

QHeaderView::section {
    background: #f8fafc;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #64748b;
}

QScrollBar:vertical {
    width: 10px;
    background: transparent;
    margin: 6px 2px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
