from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFontComboBox, QComboBox, QToolButton, QMenu, QColorDialog
)
from PyQt6.QtGui import QFont, QTextListFormat, QColor, QAction
from PyQt6.QtCore import Qt

from ui import theme

FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 24]

TEXT_COLORS = [
    ("Rouge", "#E53E3E"),
    ("Orange", "#DD6B20"),
    ("Vert", "#38A169"),
    ("Bleu", "#3182CE"),
    ("Violet", "#805AD5"),
    ("Gris", "#718096"),
]


def _looks_like_html(text):
    """Les notes enregistrées avant l'éditeur enrichi sont du texte brut : on ne les fait
    passer par setHtml() que si elles ont manifestement été produites par QTextEdit.toHtml(),
    pour ne jamais perdre les retours à la ligne d'anciennes notes en texte brut."""
    stripped = (text or '').lstrip().lower()
    return stripped.startswith('<!doctype html') or stripped.startswith('<html')


class NodeNotesDialog(QDialog):
    """Fenêtre de prise de notes détaillées associée à un nœud, avec mise en forme basique
    (police, taille, gras/italique/souligné, listes, couleur de texte) — un petit éditeur
    riche léger, tout en restant compatible avec les anciennes notes en texte brut."""

    def __init__(self, parent, node_label, initial_text):
        super().__init__(parent)
        self.setWindowTitle(f"Notes — {node_label}")
        self.resize(600, 480)

        palette = theme.get_palette(parent)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Notes du nœud :</b> {node_label}"))

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        self.font_combo = QFontComboBox(self)
        self.font_combo.setMaximumWidth(150)
        self.font_combo.currentFontChanged.connect(self._apply_font_family)
        toolbar.addWidget(self.font_combo)

        self.size_combo = QComboBox(self)
        self.size_combo.setEditable(False)
        for size in FONT_SIZES:
            self.size_combo.addItem(str(size), size)
        self.size_combo.setCurrentIndex(FONT_SIZES.index(11) if 11 in FONT_SIZES else 0)
        self.size_combo.setMaximumWidth(60)
        self.size_combo.activated.connect(self._apply_font_size)
        toolbar.addWidget(self.size_combo)

        toggle_style = theme.toggle_button_stylesheet(palette)

        self.btn_bold = QPushButton("G", self)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedWidth(28)
        self.btn_bold.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_bold.setToolTip("Gras")
        self.btn_bold.setStyleSheet(toggle_style)
        self.btn_bold.clicked.connect(self._toggle_bold)
        toolbar.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I", self)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedWidth(28)
        italic_font = QFont("Segoe UI", 10)
        italic_font.setItalic(True)
        self.btn_italic.setFont(italic_font)
        self.btn_italic.setToolTip("Italique")
        self.btn_italic.setStyleSheet(toggle_style)
        self.btn_italic.clicked.connect(self._toggle_italic)
        toolbar.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("S", self)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedWidth(28)
        underline_font = QFont("Segoe UI", 10)
        underline_font.setUnderline(True)
        self.btn_underline.setFont(underline_font)
        self.btn_underline.setToolTip("Souligné")
        self.btn_underline.setStyleSheet(toggle_style)
        self.btn_underline.clicked.connect(self._toggle_underline)
        toolbar.addWidget(self.btn_underline)

        btn_bullets = QPushButton("• Liste", self)
        btn_bullets.setToolTip("Liste à puces")
        btn_bullets.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDisc))
        toolbar.addWidget(btn_bullets)

        btn_numbers = QPushButton("1. Liste", self)
        btn_numbers.setToolTip("Liste numérotée")
        btn_numbers.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDecimal))
        toolbar.addWidget(btn_numbers)

        self.btn_color = QToolButton(self)
        self.btn_color.setText("🎨")
        self.btn_color.setToolTip("Couleur du texte")
        self.btn_color.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        color_menu = QMenu(self.btn_color)
        for name, hex_color in TEXT_COLORS:
            action = QAction(name, self)
            action.triggered.connect(lambda _, c=hex_color: self._apply_text_color(c))
            color_menu.addAction(action)
        color_menu.addSeparator()
        action_custom = QAction("Autre couleur...", self)
        action_custom.triggered.connect(self._pick_custom_color)
        color_menu.addAction(action_custom)
        action_default = QAction("Couleur par défaut", self)
        action_default.triggered.connect(lambda: self._apply_text_color(None))
        color_menu.addAction(action_default)
        self.btn_color.setMenu(color_menu)
        toolbar.addWidget(self.btn_color)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.text_edit = QTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("Écrivez ici vos notes détaillées pour ce nœud...")
        if _looks_like_html(initial_text):
            self.text_edit.setHtml(initial_text)
        else:
            self.text_edit.setPlainText(initial_text or '')
        self.text_edit.currentCharFormatChanged.connect(self._sync_toolbar_state)
        layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Enregistrer", self)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

        self.text_edit.setFocus()
        self._sync_toolbar_state(self.text_edit.currentCharFormat())

    def _apply_font_family(self, font):
        self.text_edit.setCurrentFont(font)
        self.text_edit.setFocus()

    def _apply_font_size(self, index):
        size = self.size_combo.itemData(index)
        if size:
            self.text_edit.setFontPointSize(float(size))
        self.text_edit.setFocus()

    def _toggle_bold(self, checked):
        self.text_edit.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        self.text_edit.setFocus()

    def _toggle_italic(self, checked):
        self.text_edit.setFontItalic(checked)
        self.text_edit.setFocus()

    def _toggle_underline(self, checked):
        self.text_edit.setFontUnderline(checked)
        self.text_edit.setFocus()

    def _insert_list(self, style):
        cursor = self.text_edit.textCursor()
        cursor.insertList(style)
        self.text_edit.setFocus()

    def _apply_text_color(self, hex_color):
        if hex_color:
            self.text_edit.setTextColor(QColor(hex_color))
        else:
            self.text_edit.setTextColor(QColor(theme.get_palette(self.parent())['text']))
        self.text_edit.setFocus()

    def _pick_custom_color(self):
        color = QColorDialog.getColor(self.text_edit.textColor(), self, "Choisir une couleur de texte")
        if color.isValid():
            self.text_edit.setTextColor(color)
        self.text_edit.setFocus()

    def _sync_toolbar_state(self, fmt):
        """Reflète le format sous le curseur dans la barre d'outils (gras/italique/souligné,
        police, taille), pour que les boutons enfoncés correspondent à ce qui va être tapé."""
        self.btn_bold.blockSignals(True)
        self.btn_bold.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.btn_bold.blockSignals(False)

        self.btn_italic.blockSignals(True)
        self.btn_italic.setChecked(fmt.fontItalic())
        self.btn_italic.blockSignals(False)

        self.btn_underline.blockSignals(True)
        self.btn_underline.setChecked(fmt.fontUnderline())
        self.btn_underline.blockSignals(False)

        if fmt.font().family():
            self.font_combo.blockSignals(True)
            self.font_combo.setCurrentFont(fmt.font())
            self.font_combo.blockSignals(False)

        size = int(fmt.font().pointSize())
        if size > 0:
            idx = self.size_combo.findData(size)
            if idx >= 0:
                self.size_combo.blockSignals(True)
                self.size_combo.setCurrentIndex(idx)
                self.size_combo.blockSignals(False)

    def get_text(self):
        """Renvoie le contenu enrichi (HTML) prêt à être stocké sur le nœud."""
        if not self.text_edit.toPlainText().strip():
            return ''
        return self.text_edit.toHtml()
