import math
import os
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, QPolygonF, QPainterPathStroker
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem
from signals import GraphicsSignals

BRANCH_PALETTES = [
    {'bg': '#E0F7FA', 'border': '#4DD0E1', 'text': '#333333', 'edge': '#4DD0E1'},
    {'bg': '#FFF3E0', 'border': '#FFB74D', 'text': '#333333', 'edge': '#FFB74D'},
    {'bg': '#E8F5E9', 'border': '#81C784', 'text': '#333333', 'edge': '#81C784'},
    {'bg': '#F3E5F5', 'border': '#CE93D8', 'text': '#333333', 'edge': '#CE93D8'},
    {'bg': '#FFEBEE', 'border': '#EF9A9A', 'text': '#333333', 'edge': '#EF9A9A'}
]

class NodeItem(QGraphicsItem):
    def __init__(self, node_id, label, x, y, shape='box', bg='#60A5FA', border='#3B82F6', font_color='#ffffff', file_path=None, url_link=None, is_bold=False, status='none'):
        super().__init__()
        self.node_id = node_id
        self.label = label
        self.shape_type = shape
        self.bg_color = QColor(bg)
        self.border_color = QColor(border)
        self.font_color = QColor(font_color)

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
        self.is_bold = is_bold
        self.status = status 
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

    def _get_attachment_text(self, att):
        """Méthode utilitaire pour uniformiser le préfixe textuel et tronquer les noms trop longs."""
        MAX_CHARS = 25  # 💡 Ajuste cette valeur selon tes préférences
        
        name = att.get("name", "")
        
        # Si c'est une URL, le nom commence déjà par "🔗 " dans notre logique
        if att.get("type") == "url":
            # On retire le symbole pour compter les vrais caractères du texte
            clean_name = name.replace("🔗 ", "")
            if len(clean_name) > MAX_CHARS:
                name = f"🔗 {clean_name[:MAX_CHARS]}..."
            return name
        else:
            # Pour un fichier, on tronque le nom avant d'ajouter le préfixe "📎 "
            if len(name) > MAX_CHARS:
                name = f"{name[:MAX_CHARS]}..."
            return f"📎 {name}"

    def hoverMoveEvent(self, event):
        """🟢 Change le curseur en petite main si la souris survole n'importe quelle pièce jointe (Fichier ou URL)."""
        attachments_to_draw = getattr(self, 'attachments', [])
        
        if attachments_to_draw:
            pos = event.pos()
            
            font_main = QFont('Segoe UI', 11)
            if self.is_bold: font_main.setBold(True)
            fm_main = QFontMetrics(font_main)
            text_main_height = fm_main.height() * len(self.label.split('\n'))
            main_text_rect = QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)
            
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                file_rect = QRectF(current_x, current_y, text_width, fm_att.height())
                
                # Si le curseur est sur l'élément -> Petite main
                if file_rect.contains(pos):
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                    super().hoverMoveEvent(event)
                    return
                
                current_y += fm_att.height() + 2
                
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def recalculate_size(self):
        """Calcule dynamiquement la taille du nœud selon le texte principal et la liste globale d'attachements."""
        font_main = QFont('Segoe UI', 11)
        if self.is_bold: font_main.setBold(True)
        fm_main = QFontMetrics(font_main)
        
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        lines = display_label.split('\n')
        max_width = max(fm_main.horizontalAdvance(line) for line in lines) if lines else 0
        total_height = fm_main.height() * len(lines) if lines else fm_main.height()

        # Calcul pour la liste unifiée d'attachements (Fichiers & Liens)
        attachments_to_draw = getattr(self, 'attachments', [])
        if attachments_to_draw:
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            total_height += 8 # Marge d'espacement (padding)
            
            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                w_att = fm_att.horizontalAdvance(att_text)
                if w_att > max_width:
                    max_width = w_att
                total_height += fm_att.height() + 2
        
        width = max(max_width + 30, 100)
        height = max(total_height + 20, 40)
        
        if self.shape_type == 'diamond':
            width = int(width * 1.4)
            height = int(height * 1.7)
        elif self.shape_type == 'ellipse':
            width = int(width * 1.2)
            height = max(total_height + 35, 55)

        self.rect = QRectF(-width/2, -height/2, width, height)
        self.prepareGeometryChange()

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

    def paint(self, painter, option, widget=None):
        final_bg = self.bg_color
        final_border = self.border_color
        final_text_color = self.font_color
        b_width = self.border_width

        if self.status == 'urgent':
            final_border = QColor("#E53E3E")
            b_width = 3
        elif self.status == 'progress':
            final_bg = QColor("#FEF3C7")
            final_border = QColor("#D97706")
            final_text_color = QColor("#92400E")
        elif self.status == 'done':
            final_bg = QColor("#D1FAE5")
            final_border = QColor("#059669")
            final_text_color = QColor("#065F46")

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

        # Rendu du label principal
        font_main = QFont('Segoe UI', 11)
        if self.is_bold: font_main.setBold(True)
        painter.setFont(font_main)
        painter.setPen(QPen(final_text_color))
        
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        fm_main = QFontMetrics(font_main)
        lines = display_label.split('\n')
        text_main_height = fm_main.height() * len(lines)
        
        attachments_to_draw = getattr(self, 'attachments', [])
        if attachments_to_draw:
            main_text_rect = QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)
        else:
            main_text_rect = self.rect

        painter.drawText(main_text_rect, int(Qt.AlignmentFlag.AlignCenter), display_label)

        # Rendu de la liste unifiée en dessous (Fichiers ET URLs)
        if attachments_to_draw:
            font_att = QFont('Segoe UI', 9)
            font_att.setUnderline(True) 
            painter.setFont(font_att)
            
            if final_text_color.name().lower() in ['#ffffff', '#fff']:
                painter.setPen(QPen(QColor(240, 240, 240)))
            else:
                painter.setPen(QPen(QColor(37, 99, 235))) # Couleur bleu lien hypertexte
                
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                
                painter.drawText(int(current_x), int(current_y + fm_att.ascent()), att_text)
                current_y += fm_att.height() + 2

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

            for edge in self.edges:
                edge.update_position()
            self.signals.positionChanged.emit()
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        """🟢 Intercepte de la même façon le clic sur un fichier ou sur une URL de la liste."""
        attachments_to_draw = getattr(self, 'attachments', [])
        
        if attachments_to_draw:
            pos = event.pos()
            
            font_main = QFont('Segoe UI', 11)
            if self.is_bold: font_main.setBold(True)
            fm_main = QFontMetrics(font_main)
            text_main_height = fm_main.height() * len(self.label.split('\n'))
            main_text_rect = QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)
            
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
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

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        attachments_to_draw = getattr(self, 'attachments', [])
        pos = event.pos()
        
        if attachments_to_draw:
            font_main = QFont('Segoe UI', 11)
            if self.is_bold: font_main.setBold(True)
            fm_main = QFontMetrics(font_main)
            text_main_height = fm_main.height() * len(self.label.split('\n'))
            main_text_rect = QRectF(self.rect.left(), self.rect.top() + 10, self.rect.width(), text_main_height)
            
            font_att = QFont('Segoe UI', 9)
            fm_att = QFontMetrics(font_att)
            current_y = main_text_rect.bottom() + 4
            
            for att in attachments_to_draw:
                att_text = self._get_attachment_text(att)
                text_width = fm_att.horizontalAdvance(att_text)
                current_x = self.rect.left() + (self.rect.width() - text_width) / 2
                file_rect = QRectF(current_x, current_y, text_width, fm_att.height())
                
                if file_rect.contains(pos):
                    event.accept()
                    return 
                current_y += fm_att.height() + 2

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
            # Si True -> curved, si False -> orthogonal/droit (selon ta logique)
            mode = 'curved' if self.is_curved else 'orthogonal'
        else:
            mode = getattr(scene, 'line_routing_mode', 'curved') if scene else 'curved'

        # Détermination globale des faces pour l'orientation des courbes
        dx_centers = self.dest_node.pos().x() - self.source_node.pos().x()
        dy_centers = self.dest_node.pos().y() - self.source_node.pos().y()
        
        if abs(dx_centers) > abs(dy_centers):
            start_side = "right" if dx_centers > 0 else "left"
            end_side = "left" if dx_centers > 0 else "right"
        else:
            start_side = "bottom" if dy_centers > 0 else "top"
            end_side = "top" if dy_centers > 0 else "bottom"

        # Calcul par intersection vectorielle réelle
        def get_exact_intersection(source, target):
            line = QLineF(source.pos(), target.pos())
            # Chargement de la forme vectorielle exacte du nœud mappé dans la scène
            path = source.mapToScene(source.node_shape_path())
            
            # Dichotomie sur 50 segments pour intercepter la frontière vectorielle exacte
            intersect_point = source.pos()
            for i in range(100):
                t = i / 100.0
                p = line.pointAt(t)
                if not path.contains(p):
                    intersect_point = p
                    break
            return intersect_point

        start = get_exact_intersection(self.source_node, self.dest_node)
        end = get_exact_intersection(self.dest_node, self.source_node)

        path = QPainterPath()
        path.moveTo(start)
        
        if mode == 'orthogonal':
            dx = abs(self.dest_node.pos().x() - self.source_node.pos().x())
            dy = abs(self.dest_node.pos().y() - self.source_node.pos().y())
            
            if dy > dx:
                mid_y = start.y() + (end.y() - start.y()) / 2
                path.lineTo(start.x(), mid_y)
                path.lineTo(end.x(), mid_y)
            else:
                mid_x = start.x() + (end.x() - start.x()) / 2
                path.lineTo(mid_x, start.y())
                path.lineTo(mid_x, end.y())
            path.lineTo(end)
        else:
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            
            ctrl_x1, ctrl_y1 = start.x(), start.y()
            if start_side in ('left', 'right'):
                ctrl_x1 += dx / 2
            else:
                ctrl_y1 += dy / 2

            ctrl_x2, ctrl_y2 = end.x(), end.y()
            if end_side in ('left', 'right'):
                ctrl_x2 -= dx / 2
            else:
                ctrl_y2 -= dy / 2
            
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