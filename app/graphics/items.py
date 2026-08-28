import math
import os
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QColor, QCursor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, QPixmap, QPolygonF, QPainterPathStroker
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem
from signals import GraphicsSignals

BRANCH_PALETTES = [
    {'bg': '#E0F7FA', 'border': '#4DD0E1', 'text': '#333333', 'edge': '#4DD0E1'},
    {'bg': '#FFF3E0', 'border': '#FFB74D', 'text': '#333333', 'edge': '#FFB74D'},
    {'bg': '#E8F5E9', 'border': '#81C784', 'text': '#333333', 'edge': '#81C784'},
    {'bg': '#F3E5F5', 'border': '#CE93D8', 'text': '#333333', 'edge': '#CE93D8'},
    {'bg': '#FFEBEE', 'border': '#EF9A9A', 'text': '#333333', 'edge': '#EF9A9A'}
]

MAX_CHARS_PER_LINE = 40


def compute_contrast_font_color(bg_hex):
    """Renvoie '#ffffff' ou '#000000' selon la luminance du fond, pour rester lisible."""
    color = QColor(bg_hex)
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return '#000000' if luminance > 0.6 else '#ffffff'


def wrap_line(line, max_chars=MAX_CHARS_PER_LINE):
    """Découpe une ligne trop longue en plusieurs lignes, en coupant sur les espaces si possible."""
    if len(line) <= max_chars:
        return [line]

    wrapped = []
    current = ""
    for word in line.split(' '):
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                wrapped.append(current)
                current = ""
            while len(word) > max_chars:
                wrapped.append(word[:max_chars])
                word = word[max_chars:]
            current = word
    if current:
        wrapped.append(current)
    return wrapped

class NodeItem(QGraphicsItem):
    def __init__(self, node_id, label, x, y, shape='box', bg='#60A5FA', border='#3B82F6', font_color='#ffffff',
                 file_path=None, url_link=None, is_bold=False, is_italic=False, is_strikethrough=False,
                 image_path=None, image_height=150, status='none', priority='none', is_compact=False, notes='', **kwargs):
        super().__init__()
        self.node_id = node_id
        self.label = label
        self.shape_type = shape
        self.bg_color = QColor(bg)
        self.border_color = QColor(border)
        self.font_color = QColor(font_color)

        self.date = None
        self.status = status
        self.priority = priority
        self.is_compact = is_compact
        self.notes = notes or ''

        self.attachments = []
        
        # Rétrocompatibilité lors de l'initialisation
        if file_path:
            self.attachments.append({
                "name": os.path.basename(file_path),
                "path": file_path,
                "type": "file",
                "is_local_copy": True
            })
        if url_link:
            display_name = url_link.replace("https://", "").replace("http://", "")
            self.attachments.append({
                "name": f"🔗 {display_name}",
                "path": url_link,
                "type": "url",
                "is_local_copy": False
            })

        self.file_path = None  # Obsolète
        self.url_link = None   # Obsolète (géré par self.attachments)

        # Propriétés d'image
        self.image_path = image_path
        self.image_height = image_height
        self.pixmap_cache = None
        self._last_loaded_path = None

        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_strikethrough = is_strikethrough
        self.border_width = 1
       
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(10)
        self.rect = QRectF(0, 0, 100, 40)
        self.signals = GraphicsSignals()
        self.edges = []
        self.recalculate_size()
        self.setAcceptHoverEvents(True)

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

    def get_scaled_image_size(self):
        """Calcule la taille de l'image en gardant le ratio basé sur la hauteur configurée."""
        if not self.image_path or not os.path.exists(self.image_path):
            return 0, 0
            
        if self.pixmap_cache is None or self._last_loaded_path != self.image_path:
            raw_pixmap = QPixmap(self.image_path)
            if raw_pixmap.isNull():
                return 0, 0
                
            # 🎯 AMÉLIORATION QUALITÉ : On redimensionne le Pixmap dès le chargement en cache
            # en utilisant Qt.TransformationMode.SmoothTransformation (Bilinaire/Trilinaire)
            ratio = raw_pixmap.width() / raw_pixmap.height()
            target_w = int(self.image_height * ratio)
            
            self.pixmap_cache = raw_pixmap.scaled(
                target_w, 
                self.image_height, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation # 🌟 Ligne magique pour la netteté
            )
            self._last_loaded_path = self.image_path
            
        if self.pixmap_cache.isNull():
            return 0, 0
            
        return self.pixmap_cache.width(), self.pixmap_cache.height()

    def _get_attachment_text(self, att):
        """Méthode utilitaire pour uniformiser le préfixe textuel et tronquer les noms trop longs."""
        MAX_CHARS = 25  # Ajuste cette valeur selon tes préférences
        name = att.get("name", "")
        
        if att.get("type") == "url":
            clean_name = name.replace("🔗 ", "")
            if len(clean_name) > MAX_CHARS:
                name = f"🔗 {clean_name[:MAX_CHARS]}..."
            return name
        else:
            if len(name) > MAX_CHARS:
                name = f"{name[:MAX_CHARS]}..."
            return f"📎 {name}"

    def hoverMoveEvent(self, event):
        if self.is_compact:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            super().hoverMoveEvent(event)
            return

        attachments_to_draw = getattr(self, 'attachments', [])
        has_notes = bool(getattr(self, 'notes', ''))
        if attachments_to_draw or has_notes:
            pos = event.pos()

            main_text_rect = self._get_main_text_rect()
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4

            if self.date:
                current_y += fm_att.height() + 2

            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                file_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if file_rect.contains(pos):
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                    super().hoverMoveEvent(event)
                    return

                current_y += fm_att.height() + 2

            if has_notes:
                notes_text = "📝 Notes"
                text_width = fm_att.horizontalAdvance(notes_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                notes_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if notes_rect.contains(pos):
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                    super().hoverMoveEvent(event)
                    return

        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def build_main_display_label(self):
        """Construit le texte principal (préfixe de statut + retour à la ligne automatique)."""
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        wrapped_lines = []
        for line in display_label.split('\n'):
            wrapped_lines.extend(wrap_line(line))
        return '\n'.join(wrapped_lines)

    def _get_main_text_rect(self):
        """Rectangle occupé par le texte principal (identique au calcul utilisé dans paint()),
        pour que les zones cliquables (pièces jointes, notes) restent alignées avec ce qui est affiché."""
        font_main = QFont('Segoe UI', 11)
        if self.is_bold: font_main.setBold(True)
        fm_main = QFontMetrics(font_main)
        display_label = self.build_main_display_label()
        text_main_height = fm_main.height() * len(display_label.split('\n'))
        return QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)

    def recalculate_size(self):
        """Calcule dynamiquement la taille du nœud selon le texte principal, la date et les attachements."""
        # Si une image valide est présente, la taille du nœud dépend uniquement d'elle
        if self.image_path and os.path.exists(self.image_path):
            # 🎯 FIX : On force la re-création du Pixmap mis à l'échelle pour prendre en compte la NOUVELLE hauteur
            raw_pixmap = QPixmap(self.image_path)
            if not raw_pixmap.isNull():
                ratio = raw_pixmap.width() / raw_pixmap.height()
                target_w = int(self.image_height * ratio)
                self.pixmap_cache = raw_pixmap.scaled(
                    target_w, self.image_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._last_loaded_path = self.image_path

            img_w, img_h = self.get_scaled_image_size()
            
            if img_w > 0 and img_h > 0:
                padding = 20
                width = img_w + padding
                height = img_h + padding
                
                self.rect = QRectF(-width / 2, -height / 2, width, height)
                self.prepareGeometryChange()
                if hasattr(self, 'update_edges'):
                    self.update_edges()
                return
        
        font_main = QFont('Segoe UI', 11)
        if self.is_bold: font_main.setBold(True)
        if getattr(self, 'is_italic', False):
            font_main.setItalic(True)
        if getattr(self, 'is_strikethrough', False):
            font_main.setStrikeOut(True)
        
        fm_main = QFontMetrics(font_main)

        display_label = self.build_main_display_label()
        lines = display_label.split('\n')
        max_width = max(fm_main.horizontalAdvance(line) for line in lines) if lines else 0
        total_height = fm_main.height() * len(lines) if lines else fm_main.height()

        if self.date and not self.is_compact:
            font_date = QFont('Segoe UI', 9)
            fm_date = QFontMetrics(font_date)
            date_text = f"📅 {self.date}"
            w_date = fm_date.horizontalAdvance(date_text)
            if w_date > max_width:
                max_width = w_date
            total_height += fm_date.height() + 2

        attachments_to_draw = getattr(self, 'attachments', [])
        has_notes = bool(getattr(self, 'notes', '')) and not self.is_compact
        if attachments_to_draw and not self.is_compact:
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            total_height += 8

            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                w_att = fm_att.horizontalAdvance(att_text)
                if w_att > max_width:
                    max_width = w_att
                total_height += fm_att.height() + 2

        if has_notes:
            font_notes = QFont('Segoe UI', 9)
            fm_notes = QFontMetrics(font_notes)
            if not attachments_to_draw:
                total_height += 8
            notes_text = "📝 Notes"
            w_notes = fm_notes.horizontalAdvance(notes_text)
            if w_notes > max_width:
                max_width = w_notes
            total_height += fm_notes.height() + 2

        width = max(max_width + 30, 100)
        height = max(total_height + 20, 40)
        
        if self.shape_type == 'diamond':
            width = int(width * 1.4)
            height = int(height * 1.7)
        elif self.shape_type == 'ellipse':
            width = int(width * 1.2)
            height = max(total_height + 35, 55)
        elif self.shape_type == 'parallelogram':
            width = int(width * 1.3)

        self.rect = QRectF(-width/2, -height/2, width, height)
        self.prepareGeometryChange()
        self.update_edges()

    def paint(self, painter, option, widget=None):
        # 1. Dessinez les ombres et le fond
        final_bg = self.bg_color
        final_border = self.border_color
        final_text_color = self.font_color
        b_width = self.border_width

        # 1. Gestion des couleurs de fond et de texte selon le Statut
        if self.status == 'urgent':
            final_border = QColor("#E53E3E")
            b_width = 3
        elif self.status == 'progress':
            # FIX: On ne change plus la couleur du fond ni du texte, on garde les styles par défaut
            pass
        elif self.status == 'done':
            final_bg = QColor("#D1FAE5")
            final_border = QColor("#059669")
            final_text_color = QColor("#065F46")

        # 2. FIX PRIORITÉ : Modification des bordures (si le statut n'est pas déjà 'urgent')
        if self.status != 'urgent':
            priority_val = getattr(self, 'priority', 'none')
            if priority_val in (None, 'none'):
                priority_val = 'none'
            if priority_val == 'high':
                final_border = QColor("#E53E3E") # Rouge
                b_width = 3
            elif priority_val == 'mid':
                final_border = QColor("#DD6B20") # Orange
                b_width = 3
            elif priority_val == 'none':
                # Bordure classique classique, pas de mise en forme particulière
                pass

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        
        shape_path = self.node_shape_path()
        shadow_path = QPainterPath(shape_path)
        shadow_path.translate(2, 2)
        painter.drawPath(shadow_path)

        pen = QPen(final_border, b_width)
        if self.isSelected():
            pen.setWidth(b_width + 2)
            pen.setColor(final_border.darker(150))
        painter.setPen(pen)
        painter.setBrush(QBrush(final_bg))
        painter.drawPath(shape_path)

        # 2. Gestion de l'affichage Image VS Texte
        if self.image_path and os.path.exists(self.image_path):
            img_w, img_h = self.get_scaled_image_size()
            if self.pixmap_cache and not self.pixmap_cache.isNull():
                
                # 🎯 CORRECTION : On se base sur le vrai rectangle de délimitation du nœud
                node_rect = self.boundingRect()
                
                # On calcule les coordonnées X et Y pour centrer l'image au milieu du rectangle bleu
                rect_x = node_rect.x() + (node_rect.width() - img_w) / 2
                rect_y = node_rect.y() + (node_rect.height() - img_h) / 2
                
                # Dessin de l'image au bon endroit
                painter.drawPixmap(int(rect_x), int(rect_y), img_w, img_h, self.pixmap_cache)
                return  # On coupe ici pour masquer le texte

        font_main = QFont('Segoe UI', 11)
        if self.is_bold: font_main.setBold(True)
        if getattr(self, 'is_italic', False):
            font_main.setItalic(True)
        if getattr(self, 'is_strikethrough', False):
            font_main.setStrikeOut(True)
        painter.setFont(font_main)
        painter.setPen(QPen(final_text_color))

        display_label = self.build_main_display_label()

        fm_main = QFontMetrics(font_main)
        lines = display_label.split('\n')
        text_main_height = fm_main.height() * len(lines)
        
        attachments_to_draw = getattr(self, 'attachments', [])
        if (attachments_to_draw or self.date or getattr(self, 'notes', '')) and not self.is_compact:
            main_text_rect = QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)
        else:
            main_text_rect = self.rect

        painter.drawText(main_text_rect, int(Qt.AlignmentFlag.AlignCenter), display_label)

        if self.is_compact:
            return

        current_y = main_text_rect.bottom() + 4

        if self.date:
            font_date = QFont('Segoe UI', 9)
            painter.setFont(font_date)
            painter.setPen(QPen(final_text_color.lighter(120) if final_text_color.name().lower() in ['#ffffff', '#fff'] else QColor('#4A5568')))
            fm_date = QFontMetrics(font_date)
            date_text = f"📅 {self.date}"
            text_width = fm_date.horizontalAdvance(date_text)
            current_x = self.rect.left() + (self.rect.width() - text_width) / 2
            painter.drawText(int(current_x), int(current_y + fm_date.ascent()), date_text)
            current_y += fm_date.height() + 2

        if attachments_to_draw:
            font_att = QFont('Segoe UI', 9)
            font_att.setUnderline(True) 
            painter.setFont(font_att)
            
            if final_text_color.name().lower() in ['#ffffff', '#fff']:
                painter.setPen(QPen(QColor(240, 240, 240)))
            else:
                painter.setPen(QPen(QColor(37, 99, 235)))
                
            fm_att = QFontMetrics(font_att)
            
            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2

                painter.drawText(int(current_x), int(current_y + fm_att.ascent()), att_text)
                current_y += fm_att.height() + 2

        if getattr(self, 'notes', ''):
            font_notes = QFont('Segoe UI', 9)
            font_notes.setUnderline(True)
            painter.setFont(font_notes)

            if final_text_color.name().lower() in ['#ffffff', '#fff']:
                painter.setPen(QPen(QColor(240, 240, 240)))
            else:
                painter.setPen(QPen(QColor(37, 99, 235)))

            fm_notes = QFontMetrics(font_notes)
            notes_text = "📝 Notes"
            text_width = fm_notes.horizontalAdvance(notes_text)
            current_x = self.rect.left() + (self.rect.width() - text_width) / 2

            painter.drawText(int(current_x), int(current_y + fm_notes.ascent()), notes_text)
            current_y += fm_notes.height() + 2

    def node_shape_path(self):
        path = QPainterPath()
        if self.shape_type == 'ellipse':
            path.addEllipse(self.rect)
        elif self.shape_type == 'diamond':
            path.moveTo(self.rect.left() + self.rect.width()/2, self.rect.top())
            path.lineTo(self.rect.right(), self.rect.top() + self.rect.height()/2)
            path.lineTo(self.rect.left() + self.rect.width()/2, self.rect.bottom())
            path.lineTo(self.rect.left(), self.rect.top() + self.rect.height()/2)
            path.closeSubpath()
        elif self.shape_type == 'parallelogram':
            skew = self.rect.height() * 0.35
            p1 = QPointF(self.rect.left() + skew, self.rect.top())
            p2 = QPointF(self.rect.right(), self.rect.top())
            p3 = QPointF(self.rect.right() - skew, self.rect.bottom())
            p4 = QPointF(self.rect.left(), self.rect.bottom())
            
            path.moveTo(p1)
            path.lineTo(p2)
            path.lineTo(p3)
            path.lineTo(p4)
            path.closeSubpath()
        else:
            path.addRoundedRect(self.rect, 6, 6)
        return path

    def shape(self):
        return self.node_shape_path()

    def update_edges(self):
        for edge in self.edges:
            edge.update_position()

    def boundingRect(self):
        padding = self.border_width + 6
        return self.rect.adjusted(-padding, -padding, padding, padding)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self.scene()
            if scene and getattr(scene, 'snap_to_grid', False):
                grid_size = 20
                new_pos = value
                x = round(new_pos.x() / grid_size) * grid_size
                y = round(new_pos.y() / grid_size) * grid_size
                
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
                self.setPos(x, y)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

            self.update_edges()
            self.signals.positionChanged.emit()
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        if self.is_compact:
            super().mousePressEvent(event)
            return

        attachments_to_draw = getattr(self, 'attachments', [])
        if attachments_to_draw or getattr(self, 'notes', ''):
            pos = event.pos()
            main_text_rect = self._get_main_text_rect()

            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
            if self.date:
                current_y += fm_att.height() + 2

            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                file_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if file_rect.contains(pos):
                    scene = self.scene()
                    if scene and hasattr(scene, 'views') and scene.views():
                        main_win = scene.views()[0].window()
                        if hasattr(main_win, 'attachment_controller'):
                            main_win.attachment_controller.open_specific_file(att)
                            event.accept()
                            return

                current_y += fm_att.height() + 2

            if getattr(self, 'notes', ''):
                notes_text = "📝 Notes"
                text_width = fm_att.horizontalAdvance(notes_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                notes_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if notes_rect.contains(pos):
                    scene = self.scene()
                    if scene and hasattr(scene, 'views') and scene.views():
                        main_win = scene.views()[0].window()
                        if hasattr(main_win, 'notes_controller'):
                            main_win.notes_controller.open_notes_dialog(self)
                            event.accept()
                            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.is_compact:
            self.signals.itemDoubleClicked.emit(self)
            super().mouseDoubleClickEvent(event)
            return

        attachments_to_draw = getattr(self, 'attachments', [])
        pos = event.pos()

        if attachments_to_draw or getattr(self, 'notes', ''):
            main_text_rect = self._get_main_text_rect()

            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
            if self.date:
                current_y += fm_att.height() + 2

            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                file_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if file_rect.contains(pos):
                    event.accept()
                    return
                current_y += fm_att.height() + 2

            if getattr(self, 'notes', ''):
                notes_text = "📝 Notes"
                text_width = fm_att.horizontalAdvance(notes_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                notes_rect = QRectF(current_x, current_y, text_width, fm_att.height())

                if notes_rect.contains(pos):
                    event.accept()
                    return

        self.signals.itemDoubleClicked.emit(self)
        super().mouseDoubleClickEvent(event)


class EdgeItem(QGraphicsPathItem):
    def __init__(self, edge_id, source_node, dest_node, label="", color='#A0AEC0', arrow_dir="none"):
        super().__init__()
        self.edge_id = edge_id
        self.source_node = source_node
        self.dest_node = dest_node
        self.label = label
        self.color = QColor(color)
        self.arrow_dir = arrow_dir

        self.source_node.add_edge(self)
        self.dest_node.add_edge(self)

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(0)
        self.signals = GraphicsSignals()
        self.update_position()

    def update_position(self):
        if not self.source_node or not self.dest_node:
            return

        scene = self.scene()
        if hasattr(self, 'is_curved'):
            mode = 'curved' if self.is_curved else 'orthogonal'
        else:
            mode = getattr(scene, 'line_routing_mode', 'curved') if scene else 'curved'

        # 🟢 FIX COLLAGE : Utilisation directe de self.rect mappé pour un contact au pixel près
        s_rect = self.source_node.rect
        d_rect = self.dest_node.rect
        
        s_center = self.source_node.mapToScene(s_rect.center())
        d_center = self.dest_node.mapToScene(d_rect.center())
        
        if abs(s_center.x() - d_center.x()) > abs(s_center.y() - d_center.y()):
            # Connexion Horizontale (Milieu Gauche / Droite)
            if s_center.x() < d_center.x():
                start = self.source_node.mapToScene(QPointF(s_rect.right(), s_rect.top() + s_rect.height() / 2))
                end = self.dest_node.mapToScene(QPointF(d_rect.left(), d_rect.top() + d_rect.height() / 2))
                start_side, end_side = "right", "left"
            else:
                start = self.source_node.mapToScene(QPointF(s_rect.left(), s_rect.top() + s_rect.height() / 2))
                end = self.dest_node.mapToScene(QPointF(d_rect.right(), d_rect.top() + d_rect.height() / 2))
                start_side, end_side = "left", "right"
        else:
            # Connexion Verticale (Milieu Haut / Bas)
            if s_center.y() < d_center.y():
                start = self.source_node.mapToScene(QPointF(s_rect.left() + s_rect.width() / 2, s_rect.bottom()))
                end = self.dest_node.mapToScene(QPointF(d_rect.left() + d_rect.width() / 2, d_rect.top()))
                start_side, end_side = "bottom", "top"
            else:
                start = self.source_node.mapToScene(QPointF(s_rect.left() + s_rect.width() / 2, s_rect.top()))
                end = self.dest_node.mapToScene(QPointF(d_rect.left() + d_rect.width() / 2, d_rect.bottom()))
                start_side, end_side = "top", "bottom"

        path = QPainterPath()
        path.moveTo(start)
        
        # --- MOTEUR DE ROUTAGE ---
        if mode == 'straight_diagonal':
            path.lineTo(end)
            
        elif mode == 'straight_elbow':
            if start_side in ('left', 'right'):
                corner = QPointF(start.x() + (end.x() - start.x()) / 2, end.y())
                approach_dist = min(12, abs(corner.x() - start.x()))
                approach = QPointF(corner.x() - math.copysign(approach_dist, end.x() - start.x()), start.y())
                leave_dist = min(12, abs(end.y() - corner.y()))
                leave = QPointF(corner.x(), corner.y() - math.copysign(leave_dist, end.y() - start.y()))
                
                path.lineTo(approach)
                path.quadTo(corner, leave)
            else:
                corner = QPointF(end.x(), start.y() + (end.y() - start.y()) / 2)
                approach_dist = min(12, abs(corner.y() - start.y()))
                approach = QPointF(start.x(), corner.y() - math.copysign(approach_dist, end.y() - start.y()))
                leave_dist = min(12, abs(end.x() - corner.x()))
                leave = QPointF(corner.x() - math.copysign(leave_dist, end.x() - corner.x()), corner.y())
                
                path.lineTo(approach)
                path.quadTo(corner, leave)
            path.lineTo(end)
            
        elif mode == 'orthogonal':
            if start_side in ('left', 'right'):
                mid_x = start.x() + (end.x() - start.x()) / 2
                path.lineTo(mid_x, start.y())
                path.lineTo(mid_x, end.y())
            else:
                mid_y = start.y() + (end.y() - start.y()) / 2
                path.lineTo(start.x(), mid_y)
                path.lineTo(end.x(), mid_y)
            path.lineTo(end)
            
        else:
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            
            ctrl_x1, ctrl_y1 = start.x(), start.y()
            if start_side in ('left', 'right'): ctrl_x1 += dx / 2
            else: ctrl_y1 += dy / 2

            ctrl_x2, ctrl_y2 = end.x(), end.y()
            if end_side in ('left', 'right'): ctrl_x2 -= dx / 2
            else: ctrl_y2 -= dy / 2
            
            path.cubicTo(ctrl_x1, ctrl_y1, ctrl_x2, ctrl_y2, end.x(), end.y())
        
        self.setPath(path)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(20)
        return stroker.createStroke(self.path())

    def _draw_arrow(self, painter, tip, angle, color):
        size = 12
        p1 = tip - QPointF(math.cos(angle - math.pi/6)*size, math.sin(angle - math.pi/6)*size)
        p2 = tip - QPointF(math.cos(angle + math.pi/6)*size, math.sin(angle + math.pi/6)*size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([tip, p1, p2]))

    def paint(self, painter, option, widget=None):
        pen = QPen(self.color, 3)
        if self.isSelected():
            pen.setColor(QColor('#4A90E2'))
            pen.setWidth(4)

        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        path = self.path()
        painter.drawPath(path)
        color = pen.color()

        if self.arrow_dir in ("forward", "both") and path.length() > 0:
            tip = path.pointAtPercent(1.0)
            prev = path.pointAtPercent(0.97)
            angle = math.atan2(tip.y()-prev.y(), tip.x()-prev.x())
            self._draw_arrow(painter, tip, angle, color)

        if self.arrow_dir in ("backward", "both") and path.length() > 0:
            tip = path.pointAtPercent(0.0)
            nxt = path.pointAtPercent(0.03)
            angle = math.atan2(tip.y()-nxt.y(), tip.x()-nxt.x())
            self._draw_arrow(painter, tip, angle, color)

        if self.label:
            center = path.pointAtPercent(0.5)
            font = QFont('Segoe UI', 10)
            fm = QFontMetrics(font)
            rect = QRectF(fm.boundingRect(self.label))
            rect.moveTo(center.x() - rect.width()/2, center.y() - rect.height()/2)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(248, 249, 250, 220))
            painter.drawRoundedRect(rect.adjusted(-4, -2, 4, 2), 3, 3)

            painter.setPen(QPen(QColor('#4A5568')))
            painter.setFont(font)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.label)

    def mouseDoubleClickEvent(self, event):
        self.signals.itemDoubleClicked.emit(self)
        super().mouseDoubleClickEvent(event)