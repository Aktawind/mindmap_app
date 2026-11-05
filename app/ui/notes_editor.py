"""Éditeur de texte enrichi des notes (utilisé par le panneau de notes, ui/notes_panel.py).

Une note est du HTML produit par QTextEdit.toHtml() (ou du texte brut pour les plus
anciennes). Les liens vers d'autres nœuds de la carte sont des ancres dont la cible est
"mindy-node:<id du nœud>" (ou "mindy-label:<libellé>" si le nœud n'existait pas encore
quand le lien a été écrit)."""
import os
import re
from urllib.parse import quote, unquote
from PyQt6.QtWidgets import QTextEdit, QCompleter, QToolTip
from PyQt6.QtGui import (
    QFont, QTextListFormat, QColor, QImage, QTextDocument, QTextCursor, QTextFormat,
    QPainter, QPen, QTextBlockFormat, QTextCharFormat, QTextTableFormat, QTextLength, QBrush,
    QKeySequence, QDesktopServices
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QRectF, QPointF, QEvent, QStringListModel

from services import media_service

NODE_LINK_PREFIX = "mindy-node:"
LABEL_LINK_PREFIX = "mindy-label:"
# Écart de taille des titres par rapport à la taille du texte des notes
HEADING_SIZE_STEPS = {1: 8, 2: 5, 3: 2}
HIGHLIGHT_COLORS = [
    ("Jaune", "#FEF08A"),
    ("Vert", "#BBF7D0"),
    ("Bleu", "#BFDBFE"),
    ("Rose", "#FBCFE8"),
    ("Orange", "#FED7AA"),
]
# Texte foncé posé sur le surlignage, pour rester lisible aussi en thème sombre
HIGHLIGHT_TEXT_COLOR = "#1A202C"
TABLE_BORDER_COLOR = "#A0AEC0"
_LINK_PREFIX_RE = re.compile(r'\[\[([^\[\]\n  ]{0,80})$')
_LINK_CLOSED_RE = re.compile(r'\[\[([^\[\]\n  ]+)\]\]$')


_WEB_URL_RE = re.compile(r'^(https?://|ftp://|mailto:|file:|www\.)', re.IGNORECASE)
_PLAIN_URL_RE = re.compile(r'(?:https?://|www\.)[^\s<>"]+', re.IGNORECASE)
_TYPED_URL_RE = re.compile(r'(?:^|\s)((?:https?://|www\.)[^\s<>"]+)$', re.IGNORECASE)


def _strip_url_end(url):
    """Retire la ponctuation qui suit souvent une adresse dans une phrase."""
    return url.rstrip('.,;:!?)\'"»')


def web_href(url):
    return url if re.match(r'^[a-z][a-z0-9+.-]*:', url, re.IGNORECASE) else "https://" + url


def _without_link(fmt):
    fmt = QTextCharFormat(fmt)
    fmt.setAnchor(False)
    fmt.clearProperty(QTextFormat.Property.AnchorHref)
    return fmt


def node_link_href(node_id):
    return NODE_LINK_PREFIX + node_id


def label_link_href(label):
    return LABEL_LINK_PREFIX + quote(label)


def parse_link_href(href):
    """("node", id) ou ("label", libellé) pour un lien de note, sinon None."""
    if href.startswith(NODE_LINK_PREFIX):
        return "node", href[len(NODE_LINK_PREFIX):]
    if href.startswith(LABEL_LINK_PREFIX):
        return "label", unquote(href[len(LABEL_LINK_PREFIX):])
    return None

FONT_SIZES = [9, 10, 11, 12, 14, 16, 18, 20, 24]
# Police par défaut des notes, réglable dans Fichier > Options
DEFAULT_NOTES_FONT_FAMILY = "Segoe UI"
DEFAULT_NOTES_FONT_SIZE = 10
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

def notes_default_font(settings):
    """Police par défaut des notes enregistrée dans les préférences (Fichier > Options).
    Les notes existantes gardent la police mémorisée dans leur HTML : ce réglage s'applique
    aux nouvelles notes et aux anciennes notes en texte brut."""
    family, size = DEFAULT_NOTES_FONT_FAMILY, DEFAULT_NOTES_FONT_SIZE
    if settings is not None:
        family = settings.value("notes_font_family", family, type=str) or family
        size = settings.value("notes_font_size", size, type=int) or size
    return QFont(family, size)


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
    link_activated = pyqtSignal(str)  # cible d'un lien [[Notion]] cliqué
    emoji_requested = pyqtSignal()  # Ctrl+E
    escape_pressed = pyqtSignal()

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
        self._press = None  # (position, lien sous la souris) du dernier clic
        self.link_color = "#3182CE"

        # Autocomplétion des liens : taper [[ propose les nœuds de la carte
        self._link_targets = {}  # libellé en minuscules -> id du nœud
        self._completer = QCompleter(self)
        self._completer.setModel(QStringListModel(self._completer))
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setWidget(self)
        self._completer.activated[str].connect(self._complete_link)

    # ------------------------------------------------------------------ Clavier

    def event(self, event):
        # Les raccourcis de la carte (Suppr, Entrée, Tab, Ctrl+A, Échap...) ne doivent pas
        # se déclencher pendant la saisie d'une note : l'éditeur garde toutes les touches,
        # sauf l'enregistrement et la recherche.
        if event.type() == QEvent.Type.ShortcutOverride:
            passthrough = (event.matches(QKeySequence.StandardKey.Save)
                           or (event.modifiers() & Qt.KeyboardModifier.ControlModifier
                               and event.key() in (Qt.Key.Key_F, Qt.Key.Key_R)))
            if not passthrough:
                event.accept()
                return True
        return super().event(event)

    def viewportEvent(self, event):
        # Les bulles d'aide naissent sur la zone de texte (viewport), pas sur le widget
        if event.type() == QEvent.Type.ToolTip:
            return self.event_tooltip(event)
        return super().viewportEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        popup = self._completer.popup()
        if popup.isVisible() and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab,
                                         Qt.Key.Key_Backtab, Qt.Key.Key_Escape):
            event.ignore()  # le QCompleter s'en charge
            return
        modifiers = event.modifiers()
        if key == Qt.Key.Key_E and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.emoji_requested.emit()
            return
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and not modifiers & Qt.KeyboardModifier.ControlModifier:
            backwards = key == Qt.Key.Key_Backtab or bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            if self._handle_tab(backwards):
                return
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
            self._autolink_before_cursor()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not modifiers & Qt.KeyboardModifier.ShiftModifier:
            if self._handle_return(event):
                return
        super().keyPressEvent(event)
        if event.text():
            self._after_text_typed()

    def _handle_tab(self, backwards):
        """Tab passe à la cellule suivante d'un tableau (en ajoutant une ligne à la fin) et
        décale un élément de liste d'un niveau ; Maj+Tab fait l'inverse."""
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is not None:
            cell = table.cellAt(cursor)
            index = cell.row() * table.columns() + cell.column() + (-1 if backwards else 1)
            if index < 0:
                return True
            if index >= table.rows() * table.columns():
                table.appendRows(1)
            target = table.cellAt(index // table.columns(), index % table.columns())
            self.setTextCursor(target.firstCursorPosition())
            return True
        text_list = cursor.currentList()
        if text_list is None:
            return False
        list_format = QTextListFormat(text_list.format())
        indent = list_format.indent() + (-1 if backwards else 1)
        if indent < 1:
            block_format = cursor.blockFormat()
            text_list.remove(cursor.block())
            block_format.setIndent(0)
            block_format.setMarker(QTextBlockFormat.MarkerType.NoMarker)
            cursor.setBlockFormat(block_format)
            return True
        list_format.setIndent(indent)
        if list_format.style() in (QTextListFormat.Style.ListDisc, QTextListFormat.Style.ListCircle,
                                   QTextListFormat.Style.ListSquare):
            list_format.setStyle([QTextListFormat.Style.ListDisc, QTextListFormat.Style.ListCircle,
                                  QTextListFormat.Style.ListSquare][(indent - 1) % 3])
        cursor.createList(list_format)
        return True

    def _handle_return(self, event):
        """Après un titre, la ligne suivante redevient du texte normal ; une nouvelle case
        de liste à cocher commence toujours décochée."""
        cursor = self.textCursor()
        block_format = cursor.blockFormat()
        if block_format.headingLevel() > 0 and cursor.atBlockEnd() and not cursor.hasSelection():
            block_format.setHeadingLevel(0)
            cursor.insertBlock(block_format, self._body_char_format(cursor.charFormat()))
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            return True
        if block_format.marker() == QTextBlockFormat.MarkerType.Checked:
            super().keyPressEvent(event)
            cursor = self.textCursor()
            new_format = cursor.blockFormat()
            if cursor.currentList() is not None:
                new_format.setMarker(QTextBlockFormat.MarkerType.Unchecked)
                cursor.setBlockFormat(new_format)
            return True
        return False

    # ------------------------------------------------------------------ Liens [[Notion]]

    def set_link_targets(self, targets):
        """targets : [(libellé, id du nœud)] des nœuds de la carte, pour l'autocomplétion."""
        self._link_targets = {}
        labels = []
        for label, node_id in targets:
            label = ' '.join(label.split())
            if label and label.lower() not in self._link_targets:
                self._link_targets[label.lower()] = node_id
                labels.append(label)
        labels.sort(key=str.lower)
        self._completer.model().setStringList(labels)

    def _text_before_cursor(self):
        cursor = self.textCursor()
        return cursor.block().text()[:cursor.positionInBlock()]

    def _after_text_typed(self):
        before = self._text_before_cursor()
        closed = _LINK_CLOSED_RE.search(before)
        if closed:
            self._completer.popup().hide()
            self._replace_with_link(len(closed.group(0)), closed.group(1).strip())
            return
        match = _LINK_PREFIX_RE.search(before)
        if match is None or not self._link_targets:
            self._completer.popup().hide()
            return
        self._completer.setCompletionPrefix(match.group(1))
        if self._completer.completionCount() == 0:
            self._completer.popup().hide()
            return
        popup = self._completer.popup()
        rect = self.cursorRect()
        rect.setWidth(max(180, popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width()))
        self._completer.complete(rect)
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))

    def _complete_link(self, label):
        match = _LINK_PREFIX_RE.search(self._text_before_cursor())
        if match is not None:
            self._replace_with_link(len(match.group(0)), label)

    def _replace_with_link(self, typed_length, label):
        if not label:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, typed_length)
        self._insert_link_at(cursor, self.node_href_for(label), label)

    def node_href_for(self, label):
        """Cible d'un lien vers le nœud `label` (par son id s'il existe dans la carte)."""
        node_id = self._link_targets.get(' '.join(label.split()).lower())
        return node_link_href(node_id) if node_id else label_link_href(label)

    def insert_link(self, href, text):
        """Insère un lien (vers un nœud ou une page web) à la place de la sélection, ou au
        curseur. Sans texte, la sélection elle-même devient le lien."""
        cursor = self.textCursor()
        text = text or cursor.selectedText()
        if text:
            self._insert_link_at(cursor, href, text)

    def _insert_link_at(self, cursor, href, text):
        cursor.beginEditBlock()
        base = QTextCharFormat(cursor.charFormat())
        link = QTextCharFormat(base)
        link.setAnchor(True)
        link.setAnchorHref(href)
        link.setForeground(QColor(self.link_color))
        link.setFontUnderline(True)
        cursor.insertText(text, link)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        # La suite de la saisie ne fait plus partie du lien
        self.setCurrentCharFormat(_without_link(base))

    def _autolink_before_cursor(self):
        """Transforme en lien l'adresse web qui vient d'être tapée (avant une espace ou un
        retour à la ligne)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return
        before = self._text_before_cursor()
        match = _TYPED_URL_RE.search(before)
        if not match:
            return
        url = _strip_url_end(match.group(1))
        start = cursor.position() - len(before) + match.start(1)
        target = QTextCursor(self.document())
        target.setPosition(start)
        target.setPosition(start + len(url), QTextCursor.MoveMode.KeepAnchor)
        if target.charFormat().isAnchor():
            return
        position = cursor.position()
        current = self.currentCharFormat()
        self._insert_link_at(target, web_href(url), url)
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self.setCurrentCharFormat(_without_link(current))

    def link_at(self, point):
        """("node", cible) ou ("web", adresse) du lien sous la souris — lien enregistré dans
        la note, ou adresse web écrite en clair (anciennes notes, texte collé) —, sinon None."""
        href = self.anchorAt(point.toPoint())
        if href:
            if parse_link_href(href):
                return "node", href
            if _WEB_URL_RE.match(href):
                return "web", href
            return None
        block = self.cursorForPosition(point.toPoint()).block()
        for match in _PLAIN_URL_RE.finditer(block.text()):
            url = _strip_url_end(match.group(0))
            start = QTextCursor(self.document())
            start.setPosition(block.position() + match.start())
            end = QTextCursor(self.document())
            end.setPosition(block.position() + match.start() + len(url))
            first, last = self.cursorRect(start), self.cursorRect(end)
            # Adresse sur une seule ligne : la souris doit être sur son texte
            if (first.top() == last.top() and first.left() <= point.x() <= last.right()
                    and first.top() <= point.y() <= first.bottom()):
                return "web", web_href(url)
        return None

    def _open_link(self, link):
        kind, target = link
        if kind == "node":
            self.link_activated.emit(target)
        else:
            QDesktopServices.openUrl(QUrl.fromUserInput(target))

    def event_tooltip(self, event):
        link = self.link_at(QPointF(event.pos()))
        if link and link[0] == "web":
            QToolTip.showText(event.globalPos(), f"{link[1]}\n(clic pour ouvrir)", self)
        elif link:
            QToolTip.showText(event.globalPos(), "Clic pour ouvrir la fiche de ce nœud", self)
        else:
            QToolTip.hideText()
        return True

    # ------------------------------------------------------------------ Mise en forme

    def base_point_size(self):
        return self.font().pointSizeF() if self.font().pointSizeF() > 0 else 10

    def _body_char_format(self, fmt):
        body = QTextCharFormat(fmt)
        body.setFontPointSize(self.base_point_size())
        body.setFontWeight(QFont.Weight.Normal)
        return body

    def _merge_per_fragment(self, cursor, update):
        """Applique update(format) à chaque morceau de texte de la sélection, en gardant ses
        autres attributs (police, couleur...)."""
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        cursor.beginEditBlock()
        block = self.document().findBlock(start)
        while block.isValid() and block.position() <= end:
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                f_start = max(start, fragment.position())
                f_end = min(end, fragment.position() + fragment.length())
                if f_start < f_end:
                    part = QTextCursor(self.document())
                    part.setPosition(f_start)
                    part.setPosition(f_end, QTextCursor.MoveMode.KeepAnchor)
                    fmt = fragment.charFormat()
                    update(fmt)
                    part.setCharFormat(fmt)
                it += 1
            block = block.next()
        cursor.endEditBlock()

    def set_highlight(self, color):
        """Surligne la sélection (ou la suite de la saisie) ; color=None retire le surlignage."""
        def update(fmt):
            if color:
                fmt.setBackground(QColor(color))
                fmt.setForeground(QColor(HIGHLIGHT_TEXT_COLOR))
            else:
                if fmt.foreground().color().name().lower() == HIGHLIGHT_TEXT_COLOR.lower():
                    fmt.clearForeground()
                fmt.clearBackground()
        cursor = self.textCursor()
        if cursor.hasSelection():
            self._merge_per_fragment(cursor, update)
        else:
            fmt = self.currentCharFormat()
            update(fmt)
            self.setCurrentCharFormat(fmt)

    def set_heading(self, level):
        """Titre de niveau 1 à 3 pour les paragraphes sélectionnés, 0 pour du texte normal."""
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        cursor.beginEditBlock()
        block = self.document().findBlock(start)
        size = self.base_point_size() + HEADING_SIZE_STEPS.get(level, 0)
        weight = QFont.Weight.Bold if level else QFont.Weight.Normal
        while block.isValid() and block.position() <= end:
            block_cursor = QTextCursor(block)
            block_format = block.blockFormat()
            block_format.setHeadingLevel(level)
            block_cursor.setBlockFormat(block_format)
            block_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            char_format = QTextCharFormat()
            char_format.setFontPointSize(size)
            char_format.setFontWeight(weight)
            block_cursor.mergeCharFormat(char_format)
            block_cursor.mergeBlockCharFormat(char_format)
            block = block.next()
        cursor.endEditBlock()
        char_format = self.currentCharFormat()
        char_format.setFontPointSize(size)
        char_format.setFontWeight(weight)
        self.setCurrentCharFormat(char_format)

    def insert_list(self, style):
        self.textCursor().insertList(style)

    def toggle_checklist(self):
        """Transforme les paragraphes sélectionnés en liste de cases à cocher, ou les remet
        en texte normal s'ils en sont déjà une."""
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        first = self.document().findBlock(start)
        is_checklist = first.blockFormat().marker() != QTextBlockFormat.MarkerType.NoMarker
        cursor.beginEditBlock()
        if is_checklist:
            block = first
            while block.isValid() and block.position() <= end:
                block_cursor = QTextCursor(block)
                block_format = block.blockFormat()
                block_format.setMarker(QTextBlockFormat.MarkerType.NoMarker)
                if block.textList() is not None:
                    block.textList().remove(block)
                block_format.setIndent(0)
                block_cursor.setBlockFormat(block_format)
                block = block.next()
        else:
            if cursor.currentList() is None:
                list_format = QTextListFormat()
                list_format.setStyle(QTextListFormat.Style.ListDisc)
                cursor.createList(list_format)
            block = self.document().findBlock(start)
            while block.isValid() and block.position() <= end:
                block_cursor = QTextCursor(block)
                block_format = block.blockFormat()
                block_format.setMarker(QTextBlockFormat.MarkerType.Unchecked)
                block_cursor.setBlockFormat(block_format)
                block = block.next()
        cursor.endEditBlock()

    def _checkbox_block_at(self, point):
        """Paragraphe dont la case à cocher se trouve sous la souris, sinon None."""
        block = self.cursorForPosition(point.toPoint()).block()
        if block.textList() is None or block.blockFormat().marker() == QTextBlockFormat.MarkerType.NoMarker:
            return None
        rect = self.document().documentLayout().blockBoundingRect(block)
        x = point.x() + self.horizontalScrollBar().value()
        y = point.y() + self.verticalScrollBar().value()
        line = block.layout().lineAt(0)
        line_height = line.height() if line.isValid() else rect.height()
        if rect.left() - 28 <= x < rect.left() and rect.top() <= y <= rect.top() + line_height:
            return block
        return None

    def _toggle_checkbox(self, block):
        block_format = block.blockFormat()
        checked = block_format.marker() == QTextBlockFormat.MarkerType.Checked
        block_format.setMarker(QTextBlockFormat.MarkerType.Unchecked if checked
                               else QTextBlockFormat.MarkerType.Checked)
        QTextCursor(block).setBlockFormat(block_format)

    def insert_table(self, rows, columns):
        table_format = QTextTableFormat()
        table_format.setBorder(1)
        table_format.setBorderBrush(QBrush(QColor(TABLE_BORDER_COLOR)))
        table_format.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_Solid)
        table_format.setBorderCollapse(True)
        table_format.setCellPadding(4)
        table_format.setCellSpacing(0)
        table_format.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.block().length() > 1:
            cursor.insertBlock()
        table = cursor.insertTable(rows, columns, table_format)
        cursor.endEditBlock()
        self.setTextCursor(table.cellAt(0, 0).firstCursorPosition())

    def current_table(self):
        return self.textCursor().currentTable()

    def table_insert_row(self):
        table = self.current_table()
        if table is not None:
            table.insertRows(table.cellAt(self.textCursor()).row() + 1, 1)

    def table_insert_column(self):
        table = self.current_table()
        if table is not None:
            table.insertColumns(table.cellAt(self.textCursor()).column() + 1, 1)

    def table_remove_row(self):
        table = self.current_table()
        if table is not None:
            if table.rows() <= 1:
                self._remove_table(table)
            else:
                table.removeRows(table.cellAt(self.textCursor()).row(), 1)

    def table_remove_column(self):
        table = self.current_table()
        if table is not None:
            if table.columns() <= 1:
                self._remove_table(table)
            else:
                table.removeColumns(table.cellAt(self.textCursor()).column(), 1)

    def _remove_table(self, table):
        cursor = QTextCursor(self.document())
        cursor.setPosition(table.firstPosition() - 1)
        cursor.setPosition(table.lastPosition() + 1, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

    # ------------------------------------------------------------------ Images

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

    def _set_viewport_cursor(self, shape):
        if shape != self._resize_cursor:
            self._resize_cursor = shape
            self.viewport().setCursor(shape)

    def mousePressEvent(self, event):
        self._press = None
        if event.button() == Qt.MouseButton.LeftButton:
            checkbox_block = self._checkbox_block_at(event.position())
            if checkbox_block is not None:
                self._toggle_checkbox(checkbox_block)
                event.accept()
                return
            self._press = (event.position(), self.link_at(event.position()))
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
        super().mouseMoveEvent(event)
        if hit and self._handle_rect(hit[2]).contains(point):
            shape = Qt.CursorShape.SizeFDiagCursor
        elif self.link_at(point) or self._checkbox_block_at(point) is not None:
            shape = Qt.CursorShape.PointingHandCursor
        else:
            shape = Qt.CursorShape.IBeamCursor
        self._set_viewport_cursor(shape)

    def mouseReleaseEvent(self, event):
        if self._drag:
            self._drag = None
            self._refit_images()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        # Un simple clic sur un lien [[Notion]] ouvre la fiche du nœud visé
        press, self._press = self._press, None
        if (press and press[1] and event.button() == Qt.MouseButton.LeftButton
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                and (event.position() - press[0]).manhattanLength() < 5
                and not self.textCursor().hasSelection()):
            self._open_link(press[1])

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
        if not self.textCursor().hasSelection():
            self.setTextCursor(self.cursorForPosition(event.pos()))
        if self.current_table() is not None:
            menu.addSeparator()
            add_table_actions(menu, self)
        menu.exec(event.globalPos())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        # La résolution de l'écran n'est connue qu'une fois la fenêtre affichée
        self._fit_timer.start()

    # ------------------------------------------------------------------ Contenu

    def load_note(self, notes):
        if _looks_like_html(notes):
            self.setHtml(_strip_image_sizes(notes))
        else:
            self.setPlainText(notes or '')
        self._original_images.clear()
        self._fit_timer.start()

    def note_html(self):
        """Contenu enrichi (HTML) prêt à être stocké sur le nœud, vide si la note l'est."""
        if not self.toPlainText().strip():
            return ''
        return self.toHtml()


def add_table_actions(menu, editor):
    """Actions de modification du tableau sous le curseur (menu contextuel, bouton Tableau)."""
    in_table = editor.current_table() is not None
    for text, slot in [
        ("Ajouter une ligne", editor.table_insert_row),
        ("Ajouter une colonne", editor.table_insert_column),
        ("Supprimer la ligne", editor.table_remove_row),
        ("Supprimer la colonne", editor.table_remove_column),
    ]:
        action = menu.addAction(text)
        action.setEnabled(in_table)
        action.triggered.connect(slot)
