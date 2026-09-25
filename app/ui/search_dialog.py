"""Barre de recherche/remplacement flottante (Ctrl+F / Ctrl+R), plutôt qu'un champ fixe
toujours visible dans la barre d'outils."""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt

from ui import theme

MARGIN_FROM_EDGE = 20
TOP_OFFSET = 70


class SearchReplaceBar(QFrame):
    def __init__(self, app_window):
        super().__init__(app_window)
        self.app_window = app_window
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Rechercher (libellé + notes)...")
        self.search_input.setMinimumWidth(220)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input)

        btn_close = QPushButton("✕", self)
        btn_close.setFixedSize(22, 22)
        btn_close.setToolTip("Fermer (Échap)")
        btn_close.clicked.connect(self.close_bar)
        search_row.addWidget(btn_close)
        layout.addLayout(search_row)

        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("🔁"))
        self.replace_input = QLineEdit(self)
        self.replace_input.setPlaceholderText("Remplacer par...")
        replace_row.addWidget(self.replace_input)

        self.btn_replace = QPushButton("Remplacer tout", self)
        self.btn_replace.clicked.connect(self._on_replace_all)
        replace_row.addWidget(self.btn_replace)
        layout.addLayout(replace_row)

        self.result_label = QLabel("", self)
        self.result_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.result_label)

        self.setVisible(False)
        self.refresh_style()

    def refresh_style(self):
        p = theme.get_palette(self.app_window)
        self.setStyleSheet(f"""
            QFrame {{ background: {p['bg_elevated']}; border: 1px solid {p['border']}; border-radius: 8px; }}
        """)
        self.result_label.setStyleSheet(f"font-size: 11px; color: {p['text_muted']};")

    def _on_search_changed(self, text):
        self.result_label.setText("")
        if hasattr(self.app_window, 'graph_controller'):
            self.app_window.graph_controller.filter_nodes(text)

    def _on_replace_all(self):
        search_text = self.search_input.text()
        replace_text = self.replace_input.text()
        if not search_text or not hasattr(self.app_window, 'graph_controller'):
            return
        count = self.app_window.graph_controller.replace_in_all_nodes(search_text, replace_text)
        self.result_label.setText(f"{count} remplacement(s) effectué(s)" if count else "Aucune occurrence trouvée")
        self.app_window.graph_controller.filter_nodes(self.search_input.text())

    def open_bar(self, focus_replace=False):
        self.refresh_style()
        self.reposition()
        self.setVisible(True)
        self.raise_()
        if focus_replace:
            self.replace_input.setFocus()
            self.replace_input.selectAll()
        else:
            self.search_input.setFocus()
            self.search_input.selectAll()

    def close_bar(self):
        self.setVisible(False)
        self.result_label.setText("")
        if self.search_input.text():
            self.search_input.clear()  # déclenche filter_nodes('') -> réaffiche tout
        ws = self.app_window.current_workspace() if hasattr(self.app_window, 'current_workspace') else None
        if ws is not None:
            ws.view.setFocus()

    def reposition(self):
        parent = self.app_window
        if parent is None:
            return
        self.adjustSize()
        x = parent.width() - self.width() - MARGIN_FROM_EDGE
        self.move(max(0, x), TOP_OFFSET)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(event)


def create_search_bar(app_window):
    app_window.search_bar = SearchReplaceBar(app_window)
    return app_window.search_bar
