import os
import shutil
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFontComboBox, QComboBox, QToolButton, QMenu, QColorDialog, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QFont, QTextListFormat, QColor, QAction, QImage
from PyQt6.QtCore import Qt

from ui import theme

FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 24]
MAX_NOTE_IMAGE_WIDTH = 480

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


def notes_to_plain_text(notes):
    """Convertit le contenu d'une note (HTML enrichi ou texte brut hérité) en texte simple,
    pour la recherche — réutilise le même moteur de rendu que l'éditeur (QTextDocument)
    plutôt qu'un dépouillement de balises maison, pour rester fidèle à ce qui s'affiche."""
    if not notes:
        return ''
    if _looks_like_html(notes):
        from PyQt6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setHtml(notes)
        return doc.toPlainText()
    return notes


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
        self.btn_bold.setFixedWidth(35)
        self.btn_bold.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_bold.setToolTip("Gras")
        self.btn_bold.setStyleSheet(toggle_style)
        self.btn_bold.clicked.connect(self._toggle_bold)
        toolbar.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I", self)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedWidth(35)
        italic_font = QFont("Segoe UI", 10)
        italic_font.setItalic(True)
        self.btn_italic.setFont(italic_font)
        self.btn_italic.setToolTip("Italique")
        self.btn_italic.setStyleSheet(toggle_style)
        self.btn_italic.clicked.connect(self._toggle_italic)
        toolbar.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("S", self)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedWidth(35)
        underline_font = QFont("Segoe UI", 10)
        underline_font.setUnderline(True)
        self.btn_underline.setFont(underline_font)
        self.btn_underline.setToolTip("Souligné")
        self.btn_underline.setStyleSheet(toggle_style)
        self.btn_underline.clicked.connect(self._toggle_underline)
        toolbar.addWidget(self.btn_underline)

        btn_bullets = QPushButton("• Puce", self)
        btn_bullets.setToolTip("Liste à puces")
        btn_bullets.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDisc))
        toolbar.addWidget(btn_bullets)

        btn_numbers = QPushButton("1. Liste", self)
        btn_numbers.setToolTip("Liste numérotée")
        btn_numbers.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDecimal))
        toolbar.addWidget(btn_numbers)

        self.btn_color = QToolButton(self)
        self.btn_color.setText("🎨")
        btn_color_font = QFont("Segoe UI", 10)
        self.btn_color.setFont(btn_color_font)
        self.btn_color.setFixedWidth(35)
        self.btn_color.setFixedHeight(self.btn_bold.sizeHint().height())
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

        btn_image = QPushButton("🖼️ Image", self)
        btn_image.setToolTip("Insérer une image dans la note")
        btn_image.clicked.connect(self._insert_image)
        toolbar.addWidget(btn_image)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.text_edit = QTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        # Fond de la zone de notes aligné sur celui du canevas de la carte (et non le gris-bleu
        # générique des champs de saisie), pour une continuité visuelle avec le mindmap.
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background: {palette['scene_bg']}; color: {palette['text']}; "
            f"border: 1px solid {palette['border']}; }}"
        )
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

    def closeEvent(self, event):
        # Fermer via la croix de la fenêtre doit sauvegarder comme "Enregistrer" : c'est ce
        # qu'on attend d'un éditeur de notes, pas une perte silencieuse du travail en cours.
        self.accept()
        event.accept()

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

    def _insert_image(self):
        """Copie l'image choisie dans .mindmap_attachments (même dossier que les autres
        pièces jointes) et l'insère dans la note, redimensionnée si trop large."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir une image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if not path:
            return

        try:
            target_dir = os.path.abspath(".mindmap_attachments")
            os.makedirs(target_dir, exist_ok=True)

            base_name = os.path.basename(path)
            name, ext = os.path.splitext(base_name)
            counter = 1
            new_name = base_name
            while os.path.exists(os.path.join(target_dir, new_name)):
                new_name = f"{name}_{counter}{ext}"
                counter += 1

            dest_path = os.path.join(target_dir, new_name)
            shutil.copy(path, dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'importer l'image :\n{e}")
            return

        image = QImage(dest_path)
        if image.isNull():
            QMessageBox.critical(self, "Erreur", "Ce format d'image n'est pas pris en charge.")
            return

        width_attr = f' width="{MAX_NOTE_IMAGE_WIDTH}"' if image.width() > MAX_NOTE_IMAGE_WIDTH else ''
        src = dest_path.replace('\\', '/')
        self.text_edit.textCursor().insertHtml(f'<br/><img src="{src}"{width_attr}/><br/>')
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
