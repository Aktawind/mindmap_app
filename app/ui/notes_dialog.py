"""Fenêtre de notes d'un nœud (lien « 📝 Notes » du nœud ou bouton Notes du panneau
Propriétés) : un petit éditeur enrichi, avec des liens [[Notion]] qui mènent d'une fiche à
l'autre, et une rubrique « Cité dans » qui liste les fiches renvoyant vers ce nœud."""
import html
import re
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QMenu, QComboBox, QFontComboBox,
    QColorDialog, QFileDialog, QMessageBox, QDialog, QFormLayout, QSpinBox, QDialogButtonBox,
    QPushButton, QRadioButton, QLineEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QFont, QColor, QImage, QTextListFormat
from PyQt6.QtCore import Qt

from graphics.items import NodeItem
from services import media_service
from ui import theme
from ui.emoji_picker import pick_emoji
from ui.notes_editor import (
    NoteTextEdit, FONT_SIZES, TEXT_COLORS, HIGHLIGHT_COLORS, notes_default_font, parse_link_href,
    add_table_actions, node_link_href, web_href
)

_HREF_RE = re.compile(r'href="(mindy-[^"]+)"')
HEADING_CHOICES = [("Texte", 0), ("Titre 1", 1), ("Titre 2", 2), ("Titre 3", 3)]


def _single_line(label):
    return ' '.join((label or '').split())


def _tool_button(parent, text, tooltip, font=None, checkable=False):
    button = QToolButton(parent)
    button.setText(text)
    button.setToolTip(tooltip)
    button.setCheckable(checkable)
    button.setAutoRaise(True)
    button.setFixedSize(30, 28)
    if font is not None:
        button.setFont(font)
    return button


class LinkDialog(QDialog):
    """Choix de la cible d'un lien : un nœud de la carte ou une page web."""

    def __init__(self, parent, targets, selected_text):
        super().__init__(parent)
        self.setWindowTitle("Créer un lien")
        self.resize(420, 420)
        layout = QVBoxLayout(self)

        self.to_node = QRadioButton("Vers un nœud de cette carte", self)
        self.to_node.setChecked(True)
        layout.addWidget(self.to_node)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText("Rechercher un nœud...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter)
        self.nodes = QListWidget(self)
        for label, node_id in sorted(targets, key=lambda t: t[0].lower()):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, node_id)
            self.nodes.addItem(item)
        if self.nodes.count():
            self.nodes.setCurrentRow(0)
        self.nodes.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.nodes)

        self.to_web = QRadioButton("Vers une page web", self)
        layout.addWidget(self.to_web)
        self.url = QLineEdit(self)
        self.url.setPlaceholderText("https://...")
        self.url.textEdited.connect(lambda _: self.to_web.setChecked(True))
        layout.addWidget(self.url)
        for widget in (self.filter, self.nodes):
            widget.installEventFilter(self)

        form = QFormLayout()
        self.text = QLineEdit(selected_text, self)
        self.text.setPlaceholderText("Par défaut : le nom du nœud ou l'adresse")
        form.addRow("Texte du lien :", self.text)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if not targets:
            self.to_web.setChecked(True)
            self.url.setFocus()
        else:
            self.filter.setFocus()

    def eventFilter(self, obj, event):
        # Cliquer dans la recherche ou la liste des nœuds choisit « Vers un nœud »
        if event.type() == event.Type.FocusIn:
            self.to_node.setChecked(True)
        return super().eventFilter(obj, event)

    def _apply_filter(self, text):
        self.to_node.setChecked(True)
        query = text.strip().lower()
        first = None
        for i in range(self.nodes.count()):
            item = self.nodes.item(i)
            hidden = bool(query) and query not in item.text().lower()
            item.setHidden(hidden)
            if not hidden and first is None:
                first = item
        if first is not None:
            self.nodes.setCurrentItem(first)

    def link(self):
        """(cible, texte) du lien choisi, ou None."""
        if self.to_web.isChecked():
            url = self.url.text().strip()
            return (web_href(url), self.text.text().strip() or url) if url else None
        item = self.nodes.currentItem()
        if item is None or item.isHidden():
            return None
        return node_link_href(item.data(Qt.ItemDataRole.UserRole)), self.text.text().strip() or item.text()


class TableSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insérer un tableau")
        form = QFormLayout(self)
        self.rows = QSpinBox(self)
        self.rows.setRange(1, 50)
        self.rows.setValue(3)
        self.columns = QSpinBox(self)
        self.columns.setRange(1, 12)
        self.columns.setValue(2)
        form.addRow("Lignes :", self.rows)
        form.addRow("Colonnes :", self.columns)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


def find_node(ws, node_id=None, label=None):
    """Nœud de la carte par son id, ou par son libellé (sans tenir compte de la casse)."""
    wanted = _single_line(label).lower() if label is not None else None
    for item in ws.scene.items():
        if not isinstance(item, NodeItem):
            continue
        if node_id is not None and item.node_id == node_id:
            return item
        if wanted is not None and _single_line(item.label).lower() == wanted:
            return item
    return None


class NodeNotesDialog(QDialog):
    """Fenêtre de notes du nœud. Enregistrer, la croix de fermeture et un clic sur un lien
    [[Notion]] gardent la saisie ; Annuler et Échap l'abandonnent. Après un clic sur un lien,
    `next_node` indique la fiche à ouvrir ensuite."""

    def __init__(self, app, node, ws):
        super().__init__(app)
        self.app = app
        self._node = node
        self._ws = ws
        self.next_node = None
        self.setWindowTitle(f"Notes — {_single_line(node.label)}")
        # Taille/position mémorisées à la dernière fermeture d'une fenêtre de notes (commune
        # à tous les nœuds), sinon taille par défaut
        self._settings = self.settings = getattr(app, "settings", None)
        saved_geometry = self._settings.value("notes_dialog_geometry") if self._settings is not None else None
        if saved_geometry is None or not self.restoreGeometry(saved_geometry):
            self.resize(640, 520)

        palette = theme.get_palette(app)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self.title_label = QLabel(self)
        self.title_label.setWordWrap(True)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setText(f"<b>Notes du nœud :</b> {html.escape(_single_line(node.label))}")
        layout.addWidget(self.title_label)

        self.backlinks_label = QLabel(self)
        self.backlinks_label.setWordWrap(True)
        self.backlinks_label.setTextFormat(Qt.TextFormat.RichText)
        self.backlinks_label.linkActivated.connect(self._go_to_backlink)
        layout.addWidget(self.backlinks_label)

        self._build_toolbar(self, layout)

        self.editor = NoteTextEdit(self)
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Écrivez ici vos notes détaillées pour ce nœud...\n\n"
                                       "Astuce : tapez [[ pour faire un lien vers un autre nœud.")
        # Fond de la zone de notes aligné sur celui du canevas de la carte, pour une
        # continuité visuelle avec le mindmap
        self.editor.setStyleSheet(
            f"QTextEdit {{ background: {palette['scene_bg']}; color: {palette['text']}; "
            f"border: 1px solid {palette['border']}; }}"
        )
        self.editor.link_color = palette['accent']
        self.editor.image_pasted.connect(self._insert_pasted_image)
        self.editor.image_file_dropped.connect(self._insert_image_file)
        self.editor.link_activated.connect(self.follow_link)
        self.editor.emoji_requested.connect(self._insert_emoji)
        self.editor.escape_pressed.connect(self.reject)
        self.editor.currentCharFormatChanged.connect(self._sync_toolbar_state)
        self.editor.cursorPositionChanged.connect(self._sync_block_state)
        self.editor.set_link_targets(
            [(item.label, item.node_id) for item in ws.scene.items()
             if isinstance(item, NodeItem) and item is not node]
        )
        self._loaded_notes = getattr(node, 'notes', '') or ''
        self.editor.setFont(notes_default_font(self._settings))
        self.editor.load_note(self._loaded_notes)
        self._baseline = self.editor.note_html()
        layout.addWidget(self.editor)

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

        self._show_backlinks(palette)
        self.editor.setFocus()
        self._sync_toolbar_state(self.editor.currentCharFormat())
        self._sync_block_state()

    def closeEvent(self, event):
        # Fermer via la croix de la fenêtre doit sauvegarder comme "Enregistrer" : c'est ce
        # qu'on attend d'un éditeur de notes, pas une perte silencieuse du travail en cours.
        self.accept()
        event.accept()

    def done(self, result):
        # Point de passage commun à Enregistrer, Annuler, Échap, la croix et les liens
        if self._settings is not None:
            self._settings.setValue("notes_dialog_geometry", self.saveGeometry())
        super().done(result)

    def get_text(self):
        """Contenu à stocker sur le nœud : la note d'origine telle quelle si rien n'a changé."""
        current = self.editor.note_html()
        return self._loaded_notes if current == self._baseline else current

    # ------------------------------------------------------------------ Liens

    def _show_backlinks(self, palette):
        backlinks = self._backlinks()
        if not backlinks:
            self.backlinks_label.hide()
            return
        link_style = f"color: {palette['accent']}; text-decoration: none;"
        links = " · ".join(
            f'<a href="{html.escape(item.node_id)}" style="{link_style}">'
            f'{html.escape(_single_line(item.label)) or "(sans titre)"}</a>'
            for item in backlinks
        )
        self.backlinks_label.setText(f'<span style="color: {palette["text_muted"]};">Cité dans :</span> {links}')

    def _backlinks(self):
        """Nœuds de la carte dont la fiche contient un lien vers le nœud de cette fenêtre."""
        node = self._node
        label = _single_line(node.label).lower()
        result = []
        for item in self._ws.scene.items():
            if not isinstance(item, NodeItem) or item is node or not getattr(item, 'notes', ''):
                continue
            for href in _HREF_RE.findall(item.notes):
                target = parse_link_href(html.unescape(href))
                if target and ((target[0] == "node" and target[1] == node.node_id)
                               or (target[0] == "label" and _single_line(target[1]).lower() == label)):
                    result.append(item)
                    break
        result.sort(key=lambda item: _single_line(item.label).lower())
        return result

    def follow_link(self, href):
        target = parse_link_href(href)
        if target is None:
            return
        kind, value = target
        node = find_node(self._ws, node_id=value) if kind == "node" else find_node(self._ws, label=value)
        if node is None:
            message = ("Le nœud visé par ce lien n'existe plus dans cette carte." if kind == "node"
                       else f"Aucun nœud « {value} » dans cette carte.")
            QMessageBox.information(self, "Lien", message)
            return
        self._open_next(node)

    def _go_to_backlink(self, node_id):
        node = find_node(self._ws, node_id=node_id)
        if node is not None:
            self._open_next(node)

    def _open_next(self, node):
        # Enregistre cette fiche puis laisse NotesController ouvrir celle du nœud visé
        self.next_node = node
        self.accept()

    # ------------------------------------------------------------------ Barre d'outils

    def _build_toolbar(self, parent, parent_layout):
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        self.font_combo = QFontComboBox(parent)
        self.font_combo.setMaximumWidth(190)
        self.font_combo.currentFontChanged.connect(self._apply_font_family)
        row1.addWidget(self.font_combo)

        self.size_combo = QComboBox(parent)
        for size in FONT_SIZES:
            self.size_combo.addItem(str(size), size)
        self.size_combo.setFixedWidth(52)
        self.size_combo.activated.connect(self._apply_font_size)
        row1.addWidget(self.size_combo)

        self.heading_combo = QComboBox(parent)
        for text, level in HEADING_CHOICES:
            self.heading_combo.addItem(text, level)
        self.heading_combo.setToolTip("Style du paragraphe")
        self.heading_combo.activated.connect(self._apply_heading)
        row1.addWidget(self.heading_combo)
        row1.addStretch()
        parent_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(1)
        self.btn_bold = _tool_button(parent, "G", "Gras (Ctrl+B)", QFont("Segoe UI", 10, QFont.Weight.Bold), True)
        self.btn_bold.clicked.connect(self._toggle_bold)
        italic_font = QFont("Segoe UI", 10)
        italic_font.setItalic(True)
        self.btn_italic = _tool_button(parent, "I", "Italique (Ctrl+I)", italic_font, True)
        self.btn_italic.clicked.connect(self._toggle_italic)
        underline_font = QFont("Segoe UI", 10)
        underline_font.setUnderline(True)
        self.btn_underline = _tool_button(parent, "S", "Souligné (Ctrl+U)", underline_font, True)
        self.btn_underline.clicked.connect(self._toggle_underline)
        for button in (self.btn_bold, self.btn_italic, self.btn_underline):
            row2.addWidget(button)
        row2.addSpacing(6)

        emoji_font = QFont("Segoe UI Emoji", 11)
        btn_highlight = _tool_button(parent, "🖍️", "Surligner", emoji_font)
        btn_highlight.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        highlight_menu = QMenu(btn_highlight)
        for name, hex_color in HIGHLIGHT_COLORS:
            action = highlight_menu.addAction(self._color_icon(hex_color), name)
            action.triggered.connect(lambda _, c=hex_color: self._apply_highlight(c))
        highlight_menu.addSeparator()
        highlight_menu.addAction("Aucun surlignage").triggered.connect(lambda: self._apply_highlight(None))
        btn_highlight.setMenu(highlight_menu)
        row2.addWidget(btn_highlight)

        btn_color = _tool_button(parent, "🎨", "Couleur du texte", emoji_font)
        btn_color.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        color_menu = QMenu(btn_color)
        for name, hex_color in TEXT_COLORS:
            action = color_menu.addAction(self._color_icon(hex_color), name)
            action.triggered.connect(lambda _, c=hex_color: self._apply_text_color(c))
        color_menu.addSeparator()
        color_menu.addAction("Autre couleur...").triggered.connect(self._pick_custom_color)
        color_menu.addAction("Couleur par défaut").triggered.connect(lambda: self._apply_text_color(None))
        btn_color.setMenu(color_menu)
        row2.addWidget(btn_color)

        btn_emoji = _tool_button(parent, "😀", "Insérer un emoji (Ctrl+E)", emoji_font)
        btn_emoji.clicked.connect(self._insert_emoji)
        row2.addWidget(btn_emoji)
        row2.addSpacing(6)

        btn_bullets = _tool_button(parent, "•", "Liste à puces", QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn_bullets.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDisc))
        row2.addWidget(btn_bullets)
        btn_numbers = _tool_button(parent, "1.", "Liste numérotée", QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn_numbers.clicked.connect(lambda: self._insert_list(QTextListFormat.Style.ListDecimal))
        row2.addWidget(btn_numbers)
        btn_checklist = _tool_button(parent, "☑️", "Cases à cocher (cliquez sur une case pour la cocher)", emoji_font)
        btn_checklist.clicked.connect(self._toggle_checklist)
        row2.addWidget(btn_checklist)
        row2.addSpacing(6)

        btn_link = _tool_button(parent, "🔗", "Créer un lien vers un nœud ou une page web\n"
                                "(raccourci : tapez [[ puis le nom d'un nœud)", emoji_font)
        btn_link.clicked.connect(self._create_link)
        row2.addWidget(btn_link)

        btn_table = _tool_button(parent, "▦", "Tableau", QFont("Segoe UI", 13))
        btn_table.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._table_menu = QMenu(btn_table)
        self._table_menu.aboutToShow.connect(self._fill_table_menu)
        btn_table.setMenu(self._table_menu)
        row2.addWidget(btn_table)

        btn_image = _tool_button(parent, "🖼️", "Insérer une image (ou collez-la avec Ctrl+V)", emoji_font)
        btn_image.clicked.connect(self._insert_image)
        row2.addWidget(btn_image)
        row2.addStretch()
        parent_layout.addLayout(row2)

    @staticmethod
    def _color_icon(hex_color):
        from PyQt6.QtGui import QPixmap, QIcon
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(hex_color))
        return QIcon(pixmap)

    def _fill_table_menu(self):
        self._table_menu.clear()
        self._table_menu.addAction("Insérer un tableau...").triggered.connect(self._insert_table)
        self._table_menu.addSeparator()
        add_table_actions(self._table_menu, self.editor)

    # ------------------------------------------------------------------ Actions de mise en forme

    def _apply_font_family(self, font):
        self.editor.setCurrentFont(font)
        self.editor.setFocus()

    def _apply_font_size(self, index):
        size = self.size_combo.itemData(index)
        if size:
            self.editor.setFontPointSize(float(size))
        self.editor.setFocus()

    def _apply_heading(self, index):
        self.editor.set_heading(self.heading_combo.itemData(index))
        self.editor.setFocus()

    def _toggle_bold(self, checked):
        self.editor.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)
        self.editor.setFocus()

    def _toggle_italic(self, checked):
        self.editor.setFontItalic(checked)
        self.editor.setFocus()

    def _toggle_underline(self, checked):
        self.editor.setFontUnderline(checked)
        self.editor.setFocus()

    def _apply_highlight(self, color):
        self.editor.set_highlight(color)
        self.editor.setFocus()

    def _apply_text_color(self, hex_color):
        if hex_color:
            self.editor.setTextColor(QColor(hex_color))
        else:
            self.editor.setTextColor(QColor(theme.get_palette(self.app)['text']))
        self.editor.setFocus()

    def _pick_custom_color(self):
        color = QColorDialog.getColor(self.editor.textColor(), self, "Choisir une couleur de texte")
        if color.isValid():
            self.editor.setTextColor(color)
        self.editor.setFocus()

    def _insert_list(self, style):
        self.editor.insert_list(style)
        self.editor.setFocus()

    def _toggle_checklist(self):
        self.editor.toggle_checklist()
        self.editor.setFocus()

    def _create_link(self):
        targets = [(' '.join(item.label.split()), item.node_id) for item in self._ws.scene.items()
                   if isinstance(item, NodeItem) and item is not self._node and item.label.strip()]
        dialog = LinkDialog(self, targets, self.editor.textCursor().selectedText())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            link = dialog.link()
            if link:
                self.editor.insert_link(*link)
        self.editor.setFocus()

    def _insert_table(self):
        dialog = TableSizeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editor.insert_table(dialog.rows.value(), dialog.columns.value())
        self.editor.setFocus()

    def _insert_emoji(self):
        emoji = pick_emoji(self)  # fenêtre fille de celle des notes, récents partagés
        if emoji:
            self.editor.insertPlainText(emoji)
        self.editor.setFocus()

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir une image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._insert_image_file(path)

    def _insert_image_file(self, path):
        """Copie l'image choisie dans le dossier .mindmap_attachments de la carte (même
        dossier que les autres pièces jointes) et l'insère dans la note."""
        try:
            dest_path = media_service.import_image_file(self._ws, path)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'importer l'image :\n{e}")
            return
        self._insert_image_html(dest_path)

    def _insert_pasted_image(self, image):
        """Enregistre en PNG une image collée depuis le presse-papiers puis l'insère."""
        try:
            dest_path = media_service.save_qimage(self._ws, image)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de coller l'image :\n{e}")
            return
        self._insert_image_html(dest_path)

    def _insert_image_html(self, dest_path):
        if QImage(dest_path).isNull():
            QMessageBox.critical(self, "Erreur", "Ce format d'image n'est pas pris en charge.")
            return
        # Pas de largeur fixe : NoteTextEdit ajuste l'image à la largeur du panneau
        src = dest_path.replace('\\', '/')
        self.editor.textCursor().insertHtml(f'<br/><img src="{src}"/><br/>')
        self.editor.setFocus()

    # ------------------------------------------------------------------ État de la barre

    def _sync_toolbar_state(self, fmt):
        """Reflète le format sous le curseur dans la barre d'outils."""
        for button, checked in ((self.btn_bold, fmt.fontWeight() == QFont.Weight.Bold),
                                (self.btn_italic, fmt.fontItalic()),
                                (self.btn_underline, fmt.fontUnderline() and not fmt.isAnchor())):
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)

        if fmt.font().family():
            self.font_combo.blockSignals(True)
            self.font_combo.setCurrentFont(fmt.font())
            self.font_combo.blockSignals(False)

        size = int(round(fmt.font().pointSizeF()))
        index = self.size_combo.findData(size)
        if index >= 0:
            self.size_combo.blockSignals(True)
            self.size_combo.setCurrentIndex(index)
            self.size_combo.blockSignals(False)

    def _sync_block_state(self):
        level = self.editor.textCursor().blockFormat().headingLevel()
        index = self.heading_combo.findData(level if level in (1, 2, 3) else 0)
        self.heading_combo.blockSignals(True)
        self.heading_combo.setCurrentIndex(index)
        self.heading_combo.blockSignals(False)
