import math
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
        self.file_path = file_path
        self.url_link = url_link
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

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

    def recalculate_size(self):
        font = QFont('Segoe UI', 11)
        if self.is_bold:
            font.setBold(True)
        fm = QFontMetrics(font)
        
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        if self.file_path: display_label += " 📄"
        if self.url_link: display_label += " 🔗"

        lines = display_label.split('\n')
        max_width = max(fm.horizontalAdvance(line) for line in lines) if lines else 0
        total_height = fm.height() * len(lines) if lines else fm.height()
        
        width = max(max_width + 30, 100)
        height = max(total_height + 20, 40)
        
        if self.shape_type == 'diamond':
            width = int(width * 1.4)  # Augmenté pour éviter que le texte ne sorte des pointes du losange
            height = int(height * 1.7)
        elif self.shape_type == 'ellipse':
            width = int(width * 1.2)
            height = max(total_height + 35, 55)

        self.rect = QRectF(-width/2, -height/2, width, height)
        self.prepareGeometryChange()

    def node_shape_path(self):
        """Retourne le QPainterPath précis et exact de la forme géométrique du nœud."""
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
        """Surchargé pour la détection précise des clics de souris et des intersections."""
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

        # Rendu de l'ombre portée basée sur la forme réelle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        
        shape_path = self.node_shape_path()
        shadow_path = QPainterPath(shape_path)
        shadow_path.translate(2, 2)
        painter.drawPath(shadow_path)

        # Style de bordure et sélection
        pen = QPen(final_border, b_width)
        if self.isSelected():
            pen.setWidth(b_width + 2)
            pen.setColor(final_border.darker(150))
        painter.setPen(pen)
        painter.setBrush(QBrush(final_bg))

        # Dessin de la forme principale
        painter.drawPath(shape_path)

        # Rendu du texte
        painter.setPen(QPen(final_text_color))
        font = QFont('Segoe UI', 11)
        if self.is_bold:
            font.setBold(True)
        painter.setFont(font)
        
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        if self.file_path: display_label += " 📄"
        if self.url_link: display_label += " 🔗"

        painter.drawText(self.rect, int(Qt.AlignmentFlag.AlignCenter), display_label)

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

    def mouseDoubleClickEvent(self, event):
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