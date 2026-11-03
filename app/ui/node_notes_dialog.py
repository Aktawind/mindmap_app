import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFontComboBox, QComboBox, QToolButton, QMenu, QColorDialog, QFileDialog, QMessageBox
)
from PyQt6.QtGui import (
    QFont, QTextListFormat, QColor, QAction, QImage, QTextDocument, QTextCursor, QTextFormat,
    QPainter, QPen
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QRectF, QPointF

from ui import theme
from services import media_service

FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 24]
_IMG_TAG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_IMG_WIDTH_ATTR_RE = re.compile(r'\swidth="[^"]*"', re.IGNORECASE)
_IMG_HEIGHT_ATTR_RE = re.compile(r'\sheight="[^"]*"', re.IGNORECASE)

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


def _strip_image_sizes(html):
    """Retire la largeur fixe automatique des anciennes notes (480 px, sans hauteur), pour
    que l'éditeur ajuste ces images à la fenêtre. Une taille choisie en redimensionnant
    l'image est enregistrée avec largeur ET hauteur : elle est conservée."""
    def strip(match):
        tag = match.group(0)
        return tag if _IMG_HEIGHT_ATTR_RE.search(tag) else _IMG_WIDTH_ATTR_RE.sub('', tag)
    return _IMG_TAG_RE.sub(strip, html)


def notes_to_plain_text(notes):
    """Convertit le contenu d'une note (HTML enrichi ou texte brut hérité) en texte simple,
    pour la recherche — réutilise le même moteur de rendu que l'éditeur (QTextDocument)
    plutôt qu'un dépouillement de balises maison, pour rester fidèle à ce qui s'affiche."""
    if not notes:
        return ''
    if _looks_like_html(notes):
        doc = QTextDocument()
        doc.setHtml(notes)
        return doc.toPlainText()
    return notes


class NoteTextEdit(QTextEdit):
    """Zone de texte des notes qui accepte le collage (Ctrl+V) et le glisser-déposer
    d'images : une image du presse-papiers (capture d'écran, image copiée depuis un
    navigateur...) ou un fichier image copié depuis l'explorateur."""

    image_pasted = pyqtSignal(object)  # QImage du presse-papiers
    image_file_dropped = pyqtSignal(str)  # chemin d'un fichier image

    def _image_files(self, source):
        if not source.hasUrls():
            return []
        return [url.toLocalFile() for url in source.urls()
                if url.isLocalFile() and url.toLocalFile().lower().endswith(media_service.IMAGE_EXTENSIONS)]

    def canInsertFromMimeData(self, source):
        return source.hasImage() or bool(self._image_files(source)) or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        files = self._image_files(source)
        if files:
            for path in files:
                self.image_file_dropped.emit(path)
            return
        # Une image copiée depuis un navigateur arrive aussi en HTML pointant vers l'URL
        # distante : on privilégie l'image elle-même, pour qu'elle reste lisible hors ligne.
        if source.hasImage():
            image = QImage(source.imageData())
            if not image.isNull():
                self.image_pasted.emit(image)
                return
        super().insertFromMimeData(source)

    # Taille des images : par défaut, une image occupe la largeur disponible de la fenêtre
    # sans dépasser sa taille réelle (1 pixel de l'image = 1 pixel de l'écran). On peut
    # ensuite la redimensionner en tirant la poignée de son coin inférieur droit (les
    # proportions sont conservées) ; la taille choisie est alors enregistrée avec la note.
    # Qt ne réduit les images qu'au plus proche voisin, sans lissage (texte et traits fins
    # crénelés) : on lui fournit donc une version déjà réduite avec lissage, à la résolution
    # réelle de l'écran (mise à l'échelle Windows comprise). Le fichier d'origine, lui,
    # reste en pleine résolution.

    HANDLE_SIZE = 10
    MIN_IMAGE_WIDTH = 40
    HANDLE_COLOR = "#3182CE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_images = {}
        self._hover_pos = None  # position dans le document de l'image survolée
        self._drag = None
        self._resize_cursor = False
        self.viewport().setMouseTracking(True)
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(60)
        self._fit_timer.timeout.connect(self._refit_images)

    def _available_width(self):
        """Largeur utile pour une image, indépendante de l'apparition de la barre de
        défilement (sinon l'image pourrait osciller entre deux tailles)."""
        scrollbar = self.verticalScrollBar()
        width = self.viewport().width() + (scrollbar.width() if scrollbar.isVisible() else 0)
        width -= self.style().pixelMetric(self.style().PixelMetric.PM_ScrollBarExtent)
        width -= 2 * self.document().documentMargin() + 4
        return max(50, width)

    def _original(self, src):
        original = self._original_images.get(src)
        if original is None:
            path = src[len('file:///'):] if src.lower().startswith('file:///') else src
            original = QImage(path) if os.path.isfile(path) else QImage()
            self._original_images[src] = original
        return original

    def _natural_width(self, original):
        return original.width() / self.devicePixelRatioF()

    def _display_width(self, fmt):
        """Largeur affichée : celle choisie par l'utilisateur, sinon la largeur de la fenêtre
        dans la limite de la taille réelle de l'image."""
        if fmt.width() > 0:
            return fmt.width()
        original = self._original(fmt.name())
        if original.isNull():
            return 0
        return min(self._natural_width(original), self._available_width())

    def _scaled(self, original, width):
        ratio = self.devicePixelRatioF()
        target = max(1, min(original.width(), round(width * ratio)))
        if target < original.width():
            image = original.scaledToWidth(target, Qt.TransformationMode.SmoothTransformation)
        else:
            image = QImage(original)
        image.setDevicePixelRatio(ratio)
        return image

    def loadResource(self, resource_type, name):
        if resource_type == QTextDocument.ResourceType.ImageResource.value:
            original = self._original(name.toString())
            if not original.isNull():
                return self._scaled(original, min(self._natural_width(original), self._available_width()))
        return super().loadResource(resource_type, name)

    def _image_fragments(self):
        """(position, format) de chaque image du document."""
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                fmt = fragment.charFormat()
                if fmt.isImageFormat():
                    for offset in range(fragment.length()):
                        yield fragment.position() + offset, fmt.toImageFormat()
                it += 1
            block = block.next()

    def _refit_images(self):
        doc = self.document()
        widths = {}
        for _, fmt in self._image_fragments():
            widths[fmt.name()] = self._display_width(fmt)
        for src, width in widths.items():
            original = self._original(src)
            if not original.isNull() and width > 0:
                doc.addResource(QTextDocument.ResourceType.ImageResource.value, QUrl(src),
                                self._scaled(original, width))
        doc.markContentsDirty(0, doc.characterCount())
        self.viewport().update()

    def _image_format_at(self, pos):
        cursor = QTextCursor(self.document())
        cursor.setPosition(pos + 1)
        fmt = cursor.charFormat()
        return fmt.toImageFormat() if fmt.isImageFormat() else None

    def _image_rect(self, pos, fmt):
        """Rectangle de l'image dans le viewport (images posées sur la ligne de base)."""
        original = self._original(fmt.name())
        width = self._display_width(fmt)
        if original.isNull() or width <= 0:
            return None
        height = fmt.height() if fmt.height() > 0 else width * original.height() / original.width()
        block = self.document().findBlock(pos)
        line = block.layout().lineForTextPosition(pos - block.position())
        if not line.isValid():
            return None
        cursor = QTextCursor(self.document())
        cursor.setPosition(pos)
        caret = self.cursorRect(cursor)
        return QRectF(caret.left(), caret.top() + line.ascent() - height, width, height)

    def _image_at(self, point):
        for pos, fmt in self._image_fragments():
            rect = self._image_rect(pos, fmt)
            if rect is not None and rect.adjusted(0, 0, self.HANDLE_SIZE, self.HANDLE_SIZE).contains(point):
                return pos, fmt, rect
        return None

    def _handle_rect(self, rect):
        half = self.HANDLE_SIZE
        return QRectF(rect.right() - half, rect.bottom() - half, 2 * half, 2 * half)

    def _set_image_width(self, pos, width, first_step):
        """Applique une largeur choisie (hauteur proportionnelle) ; toutes les étapes d'un
        même glisser forment une seule action pour Annuler (Ctrl+Z)."""
        fmt = self._image_format_at(pos)
        if fmt is None:
            return
        original = self._original(fmt.name())
        if original.isNull():
            return
        cursor = QTextCursor(self.document())
        cursor.setPosition(pos)
        cursor.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
        if width is None:
            fmt.clearProperty(QTextFormat.Property.ImageWidth)
            fmt.clearProperty(QTextFormat.Property.ImageHeight)
        else:
            fmt.setWidth(width)
            fmt.setHeight(round(width * original.height() / original.width()))
        if first_step:
            cursor.beginEditBlock()
        else:
            cursor.joinPreviousEditBlock()
        cursor.setCharFormat(fmt)
        cursor.endEditBlock()

    def _set_resize_cursor(self, active):
        if active != self._resize_cursor:
            self._resize_cursor = active
            self.viewport().setCursor(Qt.CursorShape.SizeFDiagCursor if active else Qt.CursorShape.IBeamCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._image_at(event.position())
            if hit and self._handle_rect(hit[2]).contains(event.position()):
                pos, fmt, rect = hit
                original = self._original(fmt.name())
                self._drag = {
                    "pos": pos,
                    "start_x": event.position().x(),
                    "start_width": rect.width(),
                    "max_width": max(self.MIN_IMAGE_WIDTH,
                                     min(self._natural_width(original), self._available_width())),
                    "first": True,
                }
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        point = event.position()
        if self._drag:
            drag = self._drag
            width = drag["start_width"] + point.x() - drag["start_x"]
            width = round(max(self.MIN_IMAGE_WIDTH, min(drag["max_width"], width)))
            self._set_image_width(drag["pos"], width, drag["first"])
            drag["first"] = False
            self._fit_timer.start()
            event.accept()
            return
        hit = self._image_at(point)
        hover_pos = hit[0] if hit else None
        if hover_pos != self._hover_pos:
            self._hover_pos = hover_pos
            self.viewport().update()
        self._set_resize_cursor(bool(hit) and self._handle_rect(hit[2]).contains(point))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag:
            self._drag = None
            self._refit_images()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._hover_pos is not None and not self._drag:
            self._hover_pos = None
            self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        pos = self._drag["pos"] if self._drag else self._hover_pos
        fmt = self._image_format_at(pos) if pos is not None else None
        rect = self._image_rect(pos, fmt) if fmt is not None else None
        if rect is None:
            return
        painter = QPainter(self.viewport())
        color = QColor(self.HANDLE_COLOR)
        painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        handle = QRectF(rect.right() - self.HANDLE_SIZE, rect.bottom() - self.HANDLE_SIZE,
                        self.HANDLE_SIZE, self.HANDLE_SIZE)
        painter.setPen(QPen(QColor("white"), 1))
        painter.setBrush(color)
        painter.drawRect(handle)
        painter.end()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        hit = self._image_at(QPointF(event.pos()))
        if hit and hit[1].width() > 0:
            menu.addSeparator()
            action = menu.addAction("Taille automatique de l'image")
            action.triggered.connect(lambda: (self._set_image_width(hit[0], None, True), self._refit_images()))
        menu.exec(event.globalPos())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        # La résolution de l'écran n'est connue qu'une fois la fenêtre affichée
        self._fit_timer.start()


class NodeNotesDialog(QDialog):
    """Fenêtre de prise de notes détaillées associée à un nœud, avec mise en forme basique
    (police, taille, gras/italique/souligné, listes, couleur de texte) — un petit éditeur
    riche léger, tout en restant compatible avec les anciennes notes en texte brut."""

    def __init__(self, parent, node_label, initial_text, workspace=None):
        super().__init__(parent)
        self._workspace = workspace
        self.setWindowTitle(f"Notes — {node_label}")
        # Taille/position mémorisées à la dernière fermeture d'une fenêtre de notes (commune
        # à tous les nœuds), sinon taille par défaut
        self._settings = getattr(parent, 'settings', None)
        saved_geometry = self._settings.value("notes_dialog_geometry") if self._settings is not None else None
        if saved_geometry is None or not self.restoreGeometry(saved_geometry):
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
        btn_image.setToolTip("Insérer une image dans la note (ou collez-la avec Ctrl+V)")
        btn_image.clicked.connect(self._insert_image)
        toolbar.addWidget(btn_image)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.text_edit = NoteTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        self.text_edit.image_pasted.connect(self._insert_pasted_image)
        self.text_edit.image_file_dropped.connect(self._insert_image_file)
        # Fond de la zone de notes aligné sur celui du canevas de la carte (et non le gris-bleu
        # générique des champs de saisie), pour une continuité visuelle avec le mindmap.
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background: {palette['scene_bg']}; color: {palette['text']}; "
            f"border: 1px solid {palette['border']}; }}"
        )
        self.text_edit.setPlaceholderText("Écrivez ici vos notes détaillées pour ce nœud...")
        if _looks_like_html(initial_text):
            self.text_edit.setHtml(_strip_image_sizes(initial_text))
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

    def done(self, result):
        # Point de passage commun à Enregistrer, Annuler, Échap et la croix de fermeture
        if self._settings is not None:
            self._settings.setValue("notes_dialog_geometry", self.saveGeometry())
        super().done(result)

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
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir une image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._insert_image_file(path)

    def _insert_image_file(self, path):
        """Copie l'image choisie dans le dossier .mindmap_attachments de la carte (même
        dossier que les autres pièces jointes) et l'insère dans la note."""
        try:
            dest_path = media_service.import_image_file(self._workspace, path)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'importer l'image :\n{e}")
            return
        self._insert_image_html(dest_path)

    def _insert_pasted_image(self, image):
        """Enregistre en PNG une image collée depuis le presse-papiers puis l'insère."""
        try:
            dest_path = media_service.save_qimage(self._workspace, image)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de coller l'image :\n{e}")
            return
        self._insert_image_html(dest_path)

    def _insert_image_html(self, dest_path):
        image = QImage(dest_path)
        if image.isNull():
            QMessageBox.critical(self, "Erreur", "Ce format d'image n'est pas pris en charge.")
            return

        # Pas de largeur fixe : NoteTextEdit ajuste l'image à la largeur de la fenêtre
        src = dest_path.replace('\\', '/')
        self.text_edit.textCursor().insertHtml(f'<br/><img src="{src}"/><br/>')
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
