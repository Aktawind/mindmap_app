"""Export des notes (menu Exporter) : chaque nœud devient un titre, suivi de sa fiche, dans
l'ordre de la carte (de la racine vers les branches, de haut en bas), en PDF ou en Word.

Les deux formats partent du même QTextDocument assemblé à partir des notes. Le PDF passe
par l'impression Qt ; le .docx est écrit directement (WordprocessingML), sans bibliothèque
supplémentaire à embarquer."""
import os
import re
import zipfile
from xml.sax.saxutils import escape

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QMarginsF, QSizeF, QUrl, Qt
from PyQt6.QtGui import (
    QFont, QGuiApplication, QImage, QPageLayout, QPageSize, QTextBlockFormat, QTextCharFormat,
    QTextCursor, QTextDocument, QTextDocumentFragment, QTextFormat, QTextListFormat, QTextTable
)
from PyQt6.QtPrintSupport import QPrinter

from graphics.items import NodeItem
from ui.notes_editor import _looks_like_html, _strip_image_sizes, parse_link_href

PAGE_MARGIN_MM = 15
A4_WIDTH_MM, A4_HEIGHT_MM = 210, 297
_PX_PER_MM = 96 / 25.4  # mise en page à 96 ppp, comme à l'écran
CONTENT_WIDTH_PX = (A4_WIDTH_MM - 2 * PAGE_MARGIN_MM) * _PX_PER_MM
CONTENT_HEIGHT_PX = (A4_HEIGHT_MM - 2 * PAGE_MARGIN_MM) * _PX_PER_MM
MAX_IMAGE_WIDTH_PX = int(CONTENT_WIDTH_PX) - 2  # une image ne dépasse jamais de la page
HEADING_POINT_SIZES = {1: 20, 2: 16, 3: 14, 4: 12, 5: 11, 6: 11}


def _image_path(name):
    return name[len('file:///'):] if name.lower().startswith('file:///') else name


class ExportDocument(QTextDocument):
    """Document d'export qui charge lui-même les images des notes (chemins locaux)."""

    def loadResource(self, resource_type, name):
        if resource_type == QTextDocument.ResourceType.ImageResource.value:
            image = QImage(_image_path(name.toString()))
            if not image.isNull():
                return image
        return super().loadResource(resource_type, name)


# ---------------------------------------------------------------------- Ordre des nœuds

def ordered_nodes(ws):
    """[(profondeur, nœud)] de la racine vers les feuilles. Les enfants de la racine se
    lisent côté droit puis côté gauche, chaque côté de haut en bas ; les sous-arbres
    détachés de la racine viennent ensuite."""
    nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
    if not nodes:
        return []
    root = next((n for n in nodes if n.node_id == 'root'), None)
    visited = set()
    result = []

    def children_of(node, is_root):
        children = [c for c in node.hierarchy_children() if c.node_id not in visited]
        if is_root:
            x = node.pos().x()
            return (sorted([c for c in children if c.pos().x() >= x], key=lambda c: c.pos().y())
                    + sorted([c for c in children if c.pos().x() < x], key=lambda c: c.pos().y()))
        return sorted(children, key=lambda c: c.pos().y())

    def walk(top):
        stack = [(top, 0)]
        visited.add(top.node_id)
        while stack:
            node, depth = stack.pop()
            result.append((depth, node))
            children = children_of(node, node is root)
            for child in children:
                visited.add(child.node_id)
            stack.extend((child, depth + 1) for child in reversed(children))

    if root is not None:
        walk(root)
    has_parent = {c.node_id for n in nodes for c in n.hierarchy_children()}
    for node in sorted(nodes, key=lambda n: (n.pos().y(), n.pos().x())):
        if node.node_id not in visited and node.node_id not in has_parent:
            walk(node)
    for node in nodes:  # cycles éventuels : rien ne doit manquer
        if node.node_id not in visited:
            walk(node)
    return result


# ---------------------------------------------------------------------- Document commun

def _note_document(notes, default_font, heading_offset):
    """Note d'un nœud préparée pour l'export : images à une taille qui tient dans la page,
    liens [[Notion]] gardés en texte coloré, titres de la note rangés sous celui du nœud."""
    doc = ExportDocument()
    doc.setDefaultFont(default_font)
    if _looks_like_html(notes):
        doc.setHtml(_strip_image_sizes(notes))
    else:
        doc.setPlainText(notes)

    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen is not None else 1.0
    block = doc.begin()
    while block.isValid():
        block_format = block.blockFormat()
        if block_format.headingLevel() > 0:
            block_format.setHeadingLevel(min(6, block_format.headingLevel() + heading_offset))
            QTextCursor(block).setBlockFormat(block_format)
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            fmt = fragment.charFormat()
            changed = False
            if fmt.isImageFormat():
                image_format = fmt.toImageFormat()
                image = QImage(_image_path(image_format.name()))
                if not image.isNull():
                    width = image_format.width() if image_format.width() > 0 else image.width() / ratio
                    width = min(width, MAX_IMAGE_WIDTH_PX)
                    image_format.setWidth(width)
                    image_format.setHeight(width * image.height() / image.width())
                    fmt = image_format
                    changed = True
            elif fmt.isAnchor() and parse_link_href(fmt.anchorHref()):
                fmt.setAnchor(False)
                fmt.clearProperty(QTextFormat.Property.AnchorHref)
                changed = True
            if changed:
                cursor = QTextCursor(doc)
                cursor.setPosition(fragment.position())
                cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(fmt)
            it += 1
        block = block.next()
    return doc


def build_document(ws, default_font):
    """QTextDocument de toutes les fiches de la carte, dans l'ordre de la carte."""
    doc = ExportDocument()
    doc.setDefaultFont(default_font)
    cursor = QTextCursor(doc)
    first = True
    for depth, node in ordered_nodes(ws):
        level = min(depth + 1, 6)
        heading_block = QTextBlockFormat()
        heading_block.setHeadingLevel(level)
        heading_block.setTopMargin(14 if level <= 2 else 10)
        heading_block.setBottomMargin(4)
        heading_char = QTextCharFormat()
        heading_char.setFont(default_font)
        heading_char.setFontPointSize(HEADING_POINT_SIZES[level])
        heading_char.setFontWeight(QFont.Weight.Bold)
        if first:
            cursor.setBlockFormat(heading_block)
            cursor.setBlockCharFormat(heading_char)
            first = False
        else:
            cursor.insertBlock(heading_block, heading_char)
        cursor.insertText(' '.join((node.label or '').split()) or "(sans titre)", heading_char)

        notes = getattr(node, 'notes', '') or ''
        if notes.strip():
            body_char = QTextCharFormat()
            body_char.setFont(default_font)
            cursor.insertBlock(QTextBlockFormat(), body_char)
            note_doc = _note_document(notes, default_font, level)
            cursor.insertFragment(QTextDocumentFragment(note_doc))
            for url, image in _document_images(note_doc):
                doc.addResource(QTextDocument.ResourceType.ImageResource.value, url, image)
    return doc


def _document_images(doc):
    names = set()
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fmt = it.fragment().charFormat()
            if fmt.isImageFormat():
                names.add(fmt.toImageFormat().name())
            it += 1
        block = block.next()
    for name in names:
        image = QImage(_image_path(name))
        if not image.isNull():
            yield QUrl(name), image


# ---------------------------------------------------------------------- PDF

def write_pdf(doc, path, title=""):
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    printer.setDocName(title)
    printer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
        QMarginsF(PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM),
        QPageLayout.Unit.Millimeter
    ))
    # Document mis en page à la taille utile de la page : sans cela, Qt ajoute sa propre
    # marge de 2 cm à celles de l'imprimante (marge de gauche trop grande, images coupées)
    doc.setDocumentMargin(0)
    doc.setPageSize(QSizeF(CONTENT_WIDTH_PX, CONTENT_HEIGHT_PX))
    doc.print(printer)


# ---------------------------------------------------------------------- Word (.docx)

_W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
         'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
         'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
         'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
_PAGE_WIDTH_TWIPS, _PAGE_HEIGHT_TWIPS = 11906, 16838  # A4
_MARGIN_TWIPS = round(PAGE_MARGIN_MM / 25.4 * 1440)
_CONTENT_WIDTH_TWIPS = _PAGE_WIDTH_TWIPS - 2 * _MARGIN_TWIPS
_EMU_PER_PX = 9525  # à 96 ppp
_WEB_LINK_RE = re.compile(r'^(https?://|ftp://|mailto:|file:)', re.IGNORECASE)
_BULLETS = ["•", "◦", "▪"]


def _xml_text(text):
    cleaned = ''.join(ch for ch in text if ch in '\t\n' or ord(ch) >= 0x20)
    return escape(cleaned)


def _hex(color):
    return color.name()[1:].upper()


class DocxWriter:
    def __init__(self, doc, default_font):
        self.doc = doc
        self.font = default_font
        self.images = []  # (nom dans word/media, octets PNG)
        self._image_ids = {}
        self._list_nums = {}  # QTextList -> (numId, puces ?)
        self.hyperlinks = {}  # adresse web -> identifiant de relation

    # -- Corps du document

    def _frame_xml(self, frame):
        parts = []
        it = frame.begin()
        while not it.atEnd():
            child = it.currentFrame()
            block = it.currentBlock()
            if child is not None:
                if isinstance(child, QTextTable):
                    parts.append(self._table_xml(child))
                else:
                    parts.append(self._frame_xml(child))
            elif block.isValid():
                parts.append(self._paragraph_xml(block))
            it += 1
        return ''.join(parts)

    def _table_xml(self, table):
        columns = max(1, table.columns())
        col_width = _CONTENT_WIDTH_TWIPS // columns
        border = f'w:val="single" w:sz="4" w:space="0" w:color="A0AEC0"'
        xml = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>']
        xml += [f'<w:{side} {border}/>' for side in ("top", "left", "bottom", "right", "insideH", "insideV")]
        xml.append('</w:tblBorders><w:tblCellMar><w:left w:w="80" w:type="dxa"/>'
                   '<w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>')
        xml += [f'<w:gridCol w:w="{col_width}"/>' for _ in range(columns)]
        xml.append('</w:tblGrid>')
        for row in range(table.rows()):
            xml.append('<w:tr>')
            for column in range(columns):
                cell = table.cellAt(row, column)
                content = ''
                if cell.isValid() and cell.row() == row and cell.column() == column:
                    # (PyQt n'expose pas l'itérateur des cellules : on parcourt leurs paragraphes)
                    parts = []
                    block = self.doc.findBlock(cell.firstCursorPosition().position())
                    while block.isValid() and block.position() <= cell.lastCursorPosition().position():
                        parts.append(self._paragraph_xml(block))
                        block = block.next()
                    content = ''.join(parts)
                xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_width}" w:type="dxa"/></w:tcPr>'
                           f'{content or "<w:p/>"}</w:tc>')
            xml.append('</w:tr>')
        xml.append('</w:tbl>')
        return ''.join(xml)

    def _paragraph_xml(self, block):
        block_format = block.blockFormat()
        ppr = []
        level = block_format.headingLevel()
        if level > 0:
            ppr.append(f'<w:pStyle w:val="Heading{min(level, 6)}"/>')
        text_list = block.textList()
        marker = block_format.marker()
        prefix = ''
        if text_list is not None and marker == QTextBlockFormat.MarkerType.NoMarker:
            num_id = self._num_id(text_list)
            ppr.append(f'<w:numPr><w:ilvl w:val="{max(0, text_list.format().indent() - 1)}"/>'
                       f'<w:numId w:val="{num_id}"/></w:numPr>')
        elif marker != QTextBlockFormat.MarkerType.NoMarker:
            prefix = "☑ " if marker == QTextBlockFormat.MarkerType.Checked else "☐ "
            indent = text_list.format().indent() if text_list is not None else 1
            ppr.append(f'<w:ind w:left="{360 * indent}"/>')
        alignment = block_format.alignment()
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            ppr.append('<w:jc w:val="center"/>')
        elif alignment & Qt.AlignmentFlag.AlignRight:
            ppr.append('<w:jc w:val="right"/>')
        elif alignment & Qt.AlignmentFlag.AlignJustify:
            ppr.append('<w:jc w:val="both"/>')

        runs = []
        if prefix:
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Segoe UI Symbol" w:hAnsi="Segoe UI Symbol"/>'
                        f'</w:rPr><w:t xml:space="preserve">{prefix}</w:t></w:r>')
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            fmt = fragment.charFormat()
            if fmt.isImageFormat():
                runs.append(self._image_xml(fmt.toImageFormat()) * fragment.text().count('￼'))
            elif fmt.isAnchor() and _WEB_LINK_RE.match(fmt.anchorHref()):
                # Lien web : cliquable dans Word
                rel_id = self._hyperlink_id(fmt.anchorHref())
                runs.append(f'<w:hyperlink r:id="{rel_id}">{self._run_xml(fragment.text(), fmt)}</w:hyperlink>')
            else:
                runs.append(self._run_xml(fragment.text(), fmt))
            it += 1
        ppr_xml = f'<w:pPr>{"".join(ppr)}</w:pPr>' if ppr else ''
        return f'<w:p>{ppr_xml}{"".join(runs)}</w:p>'

    def _num_id(self, text_list):
        key = text_list.objectIndex()
        if key not in self._list_nums:
            bullet = text_list.format().style() in (QTextListFormat.Style.ListDisc, QTextListFormat.Style.ListCircle,
                                                    QTextListFormat.Style.ListSquare)
            self._list_nums[key] = (len(self._list_nums) + 1, bullet, text_list)
        return self._list_nums[key][0]

    def _hyperlink_id(self, url):
        if url not in self.hyperlinks:
            self.hyperlinks[url] = f"rIdLink{len(self.hyperlinks) + 1}"
        return self.hyperlinks[url]

    def _run_xml(self, text, fmt):
        rpr = []
        families = fmt.fontFamilies() if fmt.hasProperty(QTextFormat.Property.FontFamilies) else None
        family = families[0] if families else None
        if family:
            f = escape(family, {'"': '&quot;'})
            rpr.append(f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>')
        if fmt.fontWeight() >= 600:
            rpr.append('<w:b/>')
        if fmt.fontItalic():
            rpr.append('<w:i/>')
        if fmt.fontStrikeOut():
            rpr.append('<w:strike/>')
        if fmt.foreground().style() != Qt.BrushStyle.NoBrush:
            rpr.append(f'<w:color w:val="{_hex(fmt.foreground().color())}"/>')
        if fmt.fontPointSize() > 0:
            rpr.append(f'<w:sz w:val="{round(fmt.fontPointSize() * 2)}"/>')
        if fmt.fontUnderline():
            rpr.append('<w:u w:val="single"/>')
        if fmt.background().style() != Qt.BrushStyle.NoBrush:
            rpr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{_hex(fmt.background().color())}"/>')
        rpr_xml = f'<w:rPr>{"".join(rpr)}</w:rPr>' if rpr else ''

        pieces = []
        for i, line in enumerate(text.split(' ')):
            if i:
                pieces.append('<w:br/>')
            for j, chunk in enumerate(line.split('\t')):
                if j:
                    pieces.append('<w:tab/>')
                if chunk:
                    pieces.append(f'<w:t xml:space="preserve">{_xml_text(chunk)}</w:t>')
        return f'<w:r>{rpr_xml}{"".join(pieces)}</w:r>' if pieces else ''

    def _image_xml(self, image_format):
        name = image_format.name()
        if name not in self._image_ids:
            image = QImage(_image_path(name))
            if image.isNull():
                return ''
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            buffer.close()
            index = len(self.images) + 1
            self.images.append((f"image{index}.png", bytes(data), image.width(), image.height()))
            self._image_ids[name] = index
        index = self._image_ids[name]
        _, _, natural_w, natural_h = self.images[index - 1]
        width = image_format.width() if image_format.width() > 0 else min(natural_w, MAX_IMAGE_WIDTH_PX)
        height = image_format.height() if image_format.height() > 0 else width * natural_h / max(1, natural_w)
        cx, cy = round(width * _EMU_PER_PX), round(height * _EMU_PER_PX)
        self._drawing_count = getattr(self, '_drawing_count', 0) + 1
        n = self._drawing_count
        return (
            f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Image {n}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="image{index}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rIdImg{index}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            f'</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
        )

    # -- Parties du paquet

    def _styles_xml(self):
        family = escape(self.font.family(), {'"': '&quot;'})
        size = round((self.font.pointSizeF() if self.font.pointSizeF() > 0 else 10) * 2)
        headings = ''.join(
            f'<w:style w:type="paragraph" w:styleId="Heading{level}"><w:name w:val="heading {level}"/>'
            f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/>'
            f'<w:pPr><w:keepNext/><w:spacing w:before="{280 if level <= 2 else 200}" w:after="80"/>'
            f'<w:outlineLvl w:val="{level - 1}"/></w:pPr>'
            f'<w:rPr><w:b/><w:sz w:val="{HEADING_POINT_SIZES[level] * 2}"/></w:rPr></w:style>'
            for level in range(1, 7)
        )
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {_W_NS}>'
            f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{family}" w:hAnsi="{family}" '
            f'w:eastAsia="{family}" w:cs="{family}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
            f'<w:lang w:val="fr-FR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
            f'<w:spacing w:after="80" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
            f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
            f'{headings}</w:styles>'
        )

    def _numbering_xml(self):
        def levels(bullet):
            xml = []
            for lvl in range(9):
                indent = 360 * (lvl + 1) + 360
                if bullet:
                    xml.append(f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
                               f'<w:lvlText w:val="{_BULLETS[lvl % 3]}"/><w:lvlJc w:val="left"/>'
                               f'<w:pPr><w:ind w:left="{indent}" w:hanging="360"/></w:pPr>'
                               f'<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/></w:rPr></w:lvl>')
                else:
                    xml.append(f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                               f'<w:lvlText w:val="%{lvl + 1}."/><w:lvlJc w:val="left"/>'
                               f'<w:pPr><w:ind w:left="{indent}" w:hanging="360"/></w:pPr></w:lvl>')
            return ''.join(xml)

        abstract = (f'<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>{levels(True)}</w:abstractNum>'
                    f'<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>{levels(False)}</w:abstractNum>')
        nums = ''.join(
            f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="{0 if bullet else 1}"/>'
            + ('' if bullet else ''.join(f'<w:lvlOverride w:ilvl="{lvl}"><w:startOverride w:val="1"/></w:lvlOverride>'
                                         for lvl in range(9)))
            + '</w:num>'
            for num_id, bullet, _ in self._list_nums.values()
        )
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering {_W_NS}>{abstract}{nums}</w:numbering>'

    def write(self, path, title=""):
        body = self._frame_xml(self.doc.rootFrame())
        section = (f'<w:sectPr><w:pgSz w:w="{_PAGE_WIDTH_TWIPS}" w:h="{_PAGE_HEIGHT_TWIPS}"/>'
                   f'<w:pgMar w:top="{_MARGIN_TWIPS}" w:right="{_MARGIN_TWIPS}" w:bottom="{_MARGIN_TWIPS}" '
                   f'w:left="{_MARGIN_TWIPS}" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
        document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_W_NS}>'
                    f'<w:body>{body}{section}</w:body></w:document>')
        link_rels = ''.join(
            f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
            f'Target="{escape(url, {chr(34): "&quot;"})}" TargetMode="External"/>' for url, rel_id in self.hyperlinks.items()
        )
        image_rels = ''.join(
            f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{name}"/>' for i, (name, _, _, _) in enumerate(self.images, start=1)
        )
        document_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
            f'{image_rels}{link_rels}</Relationships>'
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '</Types>'
        )
        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>'
        )
        core = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:title>{_xml_text(title)}</dc:title><dc:creator>Mindy</dc:creator></cp:coreProperties>'
        )
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as package:
            package.writestr('[Content_Types].xml', content_types)
            package.writestr('_rels/.rels', root_rels)
            package.writestr('docProps/core.xml', core)
            package.writestr('word/document.xml', document)
            package.writestr('word/styles.xml', self._styles_xml())
            package.writestr('word/numbering.xml', self._numbering_xml())
            package.writestr('word/_rels/document.xml.rels', document_rels)
            for name, data, _, _ in self.images:
                package.writestr(f'word/media/{name}', data)


def export_notes(ws, path, default_font):
    """Écrit les fiches de la carte dans `path` (.pdf ou .docx selon l'extension)."""
    title = os.path.splitext(os.path.basename(path))[0]
    doc = build_document(ws, default_font)
    if path.lower().endswith('.docx'):
        DocxWriter(doc, default_font).write(path, title)
    else:
        write_pdf(doc, path, title)
