from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton


class CollapsibleSection(QWidget):
    """Section repliable utilisée dans le panneau latéral des propriétés, pour regrouper des
    contrôles apparentés et laisser l'utilisateur replier ce qu'il n'utilise pas souvent."""

    def __init__(self, title, parent=None, settings=None, settings_key=None, start_expanded=True):
        super().__init__(parent)
        self._settings = settings
        self._settings_key = settings_key

        if settings is not None and settings_key:
            start_expanded = settings.value(settings_key, start_expanded, type=bool)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toggle_button = QToolButton(self)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(start_expanded)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if start_expanded else Qt.ArrowType.RightArrow)
        self.toggle_button.setStyleSheet("""
            QToolButton { border: none; font-weight: bold; padding: 6px 2px; text-align: left; color: #1e293b; }
            QToolButton:hover { background: #f1f5f9; border-radius: 4px; }
        """)
        self.toggle_button.clicked.connect(self._on_toggled)
        layout.addWidget(self.toggle_button)

        self.content = QWidget(self)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(14, 2, 4, 10)
        self.content_layout.setSpacing(6)
        layout.addWidget(self.content)
        self.content.setVisible(start_expanded)

    def _on_toggled(self, checked):
        self.content.setVisible(checked)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        if self._settings is not None and self._settings_key:
            self._settings.setValue(self._settings_key, checked)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)
