# items.py
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
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

        # Ajout discret des icônes à la fin du texte pour le calcul de la taille
        if self.file_path: display_label += " 📄"
        if self.url_link: display_label += " 🔗"

        lines = display_label.split('\n')
        max_width = max(fm.horizontalAdvance(line) for line in lines) if lines else 0
        total_height = fm.height() * len(lines) if lines else fm.height()
        
        width = max(max_width + 30, 100)
        height = max(total_height + 20, 40)
        
        if self.shape_type == 'diamond':
            width = int(width * 1.1)
            height = int(height * 1.7)
        elif self.shape_type == 'ellipse':
            height = max(total_height + 35, 55)

        self.rect = QRectF(-width/2, -height/2, width, height)
        self.prepareGeometryChange()

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
        shadow_rect = self.rect.translated(2, 2)
        if self.shape_type == 'ellipse':
            painter.drawEllipse(shadow_rect)
        elif self.shape_type == 'diamond':
            path = QPainterPath()
            path.moveTo(shadow_rect.left() + shadow_rect.width()/2, shadow_rect.top())
            path.lineTo(shadow_rect.right(), shadow_rect.top() + shadow_rect.height()/2)
            path.lineTo(shadow_rect.left() + shadow_rect.width()/2, shadow_rect.bottom())
            path.lineTo(shadow_rect.left(), shadow_rect.top() + shadow_rect.height()/2)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(shadow_rect, 6, 6)

        pen = QPen(final_border, b_width)
        if self.isSelected():
            pen.setWidth(b_width + 2)
            pen.setColor(final_border.darker(150))
        painter.setPen(pen)
        painter.setBrush(QBrush(final_bg))

        if self.shape_type == 'ellipse':
            painter.drawEllipse(self.rect)
        elif self.shape_type == 'diamond':
            path = QPainterPath()
            path.moveTo(self.rect.left() + self.rect.width()/2, self.rect.top())
            path.lineTo(self.rect.right(), self.rect.top() + self.rect.height()/2)
            path.lineTo(self.rect.left() + self.rect.width()/2, self.rect.bottom())
            path.lineTo(self.rect.left(), self.rect.top() + self.rect.height()/2)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(self.rect, 6, 6)

        painter.setPen(QPen(final_text_color))
        font = QFont('Segoe UI', 11)
        if self.is_bold:
            font.setBold(True)
        painter.setFont(font)
        
        display_label = self.label
        if self.status == 'urgent' and not display_label.startswith("🚨 "): display_label = "🚨 " + display_label
        elif self.status == 'progress' and not display_label.startswith("⏳ "): display_label = "⏳ " + display_label
        elif self.status == 'done' and not display_label.startswith("✅ "): display_label = "✅ " + display_label

        # Ajout discret des icônes uniquement à l'affichage
        if self.file_path: display_label += " 📄"
        if self.url_link: display_label += " 🔗"

        painter.drawText(self.rect, int(Qt.AlignmentFlag.AlignCenter), display_label)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
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
        mode = getattr(scene, 'line_routing_mode', 'curved') if scene else 'curved'

        s_center = self.source_node.pos()
        d_center = self.dest_node.pos()

        w_s = self.source_node.rect.width() / 2
        w_d = self.dest_node.rect.width() / 2

        # Ancrage latéral intelligent (gauche/droite) pour s'aligner avec le rendu horizontal
        if d_center.x() >= s_center.x():
            start = QPointF(s_center.x() + w_s, s_center.y())
            end = QPointF(d_center.x() - w_d, d_center.y())
            # Recul de 2px pour rendre la pointe de la flèche parfaitement visible devant le nœud
            start = QPointF(start.x() + 2, start.y())
            end = QPointF(end.x() - 2, end.y())
        else:
            start = QPointF(s_center.x() - w_s, s_center.y())
            end = QPointF(d_center.x() + w_d, d_center.y())
            start = QPointF(start.x() - 2, start.y())
            end = QPointF(end.x() + 2, end.y())

        path = QPainterPath()
        path.moveTo(start)

        if mode == 'orthogonal':
            mid_x = (start.x() + end.x()) / 2
            path.lineTo(mid_x, start.y())
            path.lineTo(mid_x, end.y())
            path.lineTo(end)
        else:
            ctrl_x = (start.x() + end.x()) / 2
            path.cubicTo(ctrl_x, start.y(), ctrl_x, end.y(), end.x(), end.y())

        self.setPath(path)
        self.update()

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(20)
        return stroker.createStroke(self.path())

    def _draw_arrow(self, painter, tip, angle, color):
        size = 12
        p1 = tip - QPointF(math.cos(angle - math.pi/6)*size,
                           math.sin(angle - math.pi/6)*size)
        p2 = tip - QPointF(math.cos(angle + math.pi/6)*size,
                           math.sin(angle + math.pi/6)*size)
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
