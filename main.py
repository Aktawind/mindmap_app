import sys
import os
import json
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsPathItem, QFileDialog, 
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QComboBox, QTextEdit, QTabWidget, QInputDialog
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, 
    QKeySequence, QDesktopServices, QPixmap, QShortcut, QPainterPathStroker, QIcon, QCloseEvent, QPolygonF
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QObject, QUrl, QSettings, QTimer, QPointF

# --- PALETTES DE COULEURS ---
BRANCH_PALETTES = [
    {'bg': '#E0F7FA', 'border': '#4DD0E1', 'text': '#333333', 'edge': '#4DD0E1'},
    {'bg': '#FFF3E0', 'border': '#FFB74D', 'text': '#333333', 'edge': '#FFB74D'},
    {'bg': '#E8F5E9', 'border': '#81C784', 'text': '#333333', 'edge': '#81C784'},
    {'bg': '#F3E5F5', 'border': '#CE93D8', 'text': '#333333', 'edge': '#CE93D8'},
    {'bg': '#FFEBEE', 'border': '#EF9A9A', 'text': '#333333', 'edge': '#EF9A9A'}
]

class GraphicsSignals(QObject):
    itemDoubleClicked = pyqtSignal(object)
    selectionChanged = pyqtSignal()
    positionChanged = pyqtSignal()

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

    def paint(self, painter):
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

class MindMapScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor('#f8f9fa'))
        self.signals = GraphicsSignals()
        self.line_routing_mode = 'curved'

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if not item:
            self.signals.itemDoubleClicked.emit(event.scenePos())
        super().mouseDoubleClickEvent(event)


class MindMapControlView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setStyleSheet("border: none;")
        
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.position().toPoint())
            if not item:
                self._is_panning = True
                self._pan_start_x = event.position().x()
                self._pan_start_y = event.position().y()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            dx = event.position().x() - self._pan_start_x
            dy = event.position().y() - self._pan_start_y
            
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(dx))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(dy))
            
            self._pan_start_x = event.position().x()
            self._pan_start_y = event.position().y()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        current_scale = self.transform().m11()
        angle = event.angleDelta().y()

        if angle > 0 and current_scale < 3.0:
            zoom_factor = zoom_in_factor
        elif angle < 0 and current_scale > 0.3:
            zoom_factor = zoom_out_factor
        else:
            zoom_factor = 1.0

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(zoom_factor, zoom_factor)
        event.accept()


class MindMapWorkspace(QWidget):
    def __init__(self, main_app, file_path=None):
        super().__init__()
        self.main_app = main_app
        self.current_file_path = file_path
        self.undo_stack = []
        self.redo_stack = []
        self.is_applying_state = False
        self.is_dirty = False

        self.scene = MindMapScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        
        self.scene.selectionChanged.connect(self.main_app.on_selection_changed)
        self.scene.signals.itemDoubleClicked.connect(self.main_app.on_bg_double_clicked)
        
        self.view = MindMapControlView(self.scene, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.centerOn(0, 0)


class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mindy - MindMap App")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        self.load_last_project_on_startup()

    def current_workspace(self) -> MindMapWorkspace:
        return self.tab_widget.currentWidget()

    def create_separator(self):
        sep = QWidget()
        sep.setFixedSize(2, 22)
        sep.setStyleSheet("background-color: #cbd5e1; margin: 0 4px;")
        return sep

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Fichier")
        file_menu.addAction("📄 Nouveau projet", lambda: self.new_project())
        file_menu.addSeparator()
        file_menu.addAction("📂 Ouvrir un projet", self.load_project)
        file_menu.addAction("💾 Enregistrer", self.save_project).setShortcut("Ctrl+S")
        file_menu.addAction("💾 Enregistrer sous...", lambda: self.save_project(force_save_as=True))
        
        edit_menu = menu_bar.addMenu("Édition")
        edit_menu.addAction("↩️ Annuler", self.undo).setShortcut("Ctrl+Z")
        edit_menu.addAction("↪️ Rétablir", self.redo).setShortcut("Ctrl+Y")
        
        export_menu = menu_bar.addMenu("Exporter")
        export_menu.addAction("Exporter en Image", self.export_png)
        export_menu.addAction("Exporter en Markdown", self.export_md)

        self.header_right_widget = QWidget()
        hr_layout = QHBoxLayout(self.header_right_widget)
        hr_layout.setContentsMargins(0, 0, 10, 0)
        
        self.routing_combo = QComboBox()
        self.routing_combo.addItem("Branches Courbes", "curved")
        self.routing_combo.addItem("Branches Droites", "orthogonal")
        self.routing_combo.setStyleSheet("padding: 2px 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.routing_combo.currentIndexChanged.connect(self.change_global_routing)
        hr_layout.addWidget(self.routing_combo)

        self.template_combo = QComboBox()
        self.template_combo.addItem("Choisir un template...")
        self.template_combo.addItem("🎯 Cadrage d'Idée", "cadrage_idee.json")
        self.template_combo.addItem("🔍 Résolution de Problème", "resolution_probleme.json")
        self.template_combo.addItem("⏳ Organisation des priorités", "gestion_temps.json")
        self.template_combo.addItem("🧠 Brain Dump", "brain_dump.json")
        self.template_combo.addItem("🚀 Onboarding Technique", "onboarding_technique.json")
        self.template_combo.addItem("🎨 Hub Multi-Passions", "hub_passions.json")
        self.template_combo.addItem("✈️ Organisation d'un Voyage", "organisation_voyage.json")
        self.template_combo.addItem("🗣️ Préparation Réunion/Entretien", "preparation_reunion.json")
        self.template_combo.addItem("🏁 Rétrospective de Fin de Projet", "retro_projet.json")
        self.template_combo.addItem("☀️ Daily Capsule", "daily_capsule.json")
        self.template_combo.addItem("🔋 Santé Mentale et Énergie", "sante_mentale_energie.json")
        self.template_combo.addItem("🚨 Urgence Colère", "urgence_colere.json")
        self.template_combo.setStyleSheet("margin: 2px 10px; padding: 2px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.template_combo.currentIndexChanged.connect(self.apply_template)
        hr_layout.addWidget(self.template_combo)
        
        menu_bar.setCornerWidget(self.header_right_widget, Qt.Corner.TopRightCorner)

        self.style_bar = QFrame(self)
        self.style_bar.setStyleSheet("""
            QFrame { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }
            QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 12px; }
            QPushButton:hover { background: #e2e8f0; }
            QComboBox { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 4px; border-radius: 8px; min-width: 110px; }
        """)
        style_layout = QHBoxLayout(self.style_bar)
        
        self.node_controls = QWidget()
        nc_layout = QHBoxLayout(self.node_controls)
        nc_layout.setContentsMargins(0,0,0,0)
        
        btn_bold = QPushButton("Bold")
        btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_bold.setFixedSize(38, 26)
        btn_bold.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
        btn_bold.clicked.connect(self.toggle_bold)
        nc_layout.addWidget(btn_bold)
        
        nc_layout.addWidget(self.create_separator())
        
        self.shape_combo = QComboBox()
        self.shape_combo.addItem("Rectangle", "box")
        self.shape_combo.addItem("Losange", "diamond")
        self.shape_combo.addItem("Ellipse", "ellipse")
        self.shape_combo.currentIndexChanged.connect(self.on_shape_combo_changed)
        nc_layout.addWidget(self.shape_combo)
        
        nc_layout.addWidget(self.create_separator())

        self.status_combo = QComboBox()
        self.status_combo.addItem("⚪ Aucun statut", "none")
        self.status_combo.addItem("🚨 Urgent", "urgent")
        self.status_combo.addItem("⏳ En cours", "progress")
        self.status_combo.addItem("✅ Terminé", "done")
        self.status_combo.currentIndexChanged.connect(self.on_status_combo_changed)
        nc_layout.addWidget(self.status_combo)

        nc_layout.addWidget(self.create_separator())
        
        for color, border in [('#60A5FA', '#3B82F6'), ('#E0F7FA', '#4DD0E1'), ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'), ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')]:            
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background: {color}; border: 2px solid {border}; border-radius: 11px;")
            btn.clicked.connect(lambda checked, c=color, b=border: self.change_color(c, b))
            nc_layout.addWidget(btn)
            
        nc_layout.addWidget(self.create_separator())
        
        btn_attach = QPushButton("📎 Fichier")
        btn_attach.clicked.connect(self.attach_file)
        nc_layout.addWidget(btn_attach)
        
        btn_url = QPushButton("🔗 URL")
        btn_url.clicked.connect(self.attach_url)
        nc_layout.addWidget(btn_url)
        
        self.btn_open = QPushButton("📂 Ouvrir")
        self.btn_open.setStyleSheet("background: #2D3748; color: white;")
        self.btn_open.clicked.connect(self.open_file)
        nc_layout.addWidget(self.btn_open)

        self.btn_detach = QPushButton("❌ Dissocier")
        self.btn_detach.setStyleSheet("background: #FED7D7; color: #C53030;")
        self.btn_detach.clicked.connect(self.detach_links)
        nc_layout.addWidget(self.btn_detach)
        
        style_layout.addWidget(self.node_controls)
        
        self.edge_controls = QWidget()
        ec_layout = QHBoxLayout(self.edge_controls)
        ec_layout.setContentsMargins(0,0,0,0)
        
        btn_edit_edge = QPushButton("Texte de branche")
        btn_edit_edge.clicked.connect(self.edit_selected_edge)
        ec_layout.addWidget(btn_edit_edge)
        
        ec_layout.addWidget(self.create_separator())
        
        self.arrow_combo = QComboBox()
        self.arrow_combo.addItem("➖ Aucune flèche", "none")
        self.arrow_combo.addItem("➡️ Flèche Avant", "forward")
        self.arrow_combo.addItem("⬅️ Flèche Arrière", "backward")
        self.arrow_combo.addItem("↔️ Double flèche", "both")
        self.arrow_combo.currentIndexChanged.connect(self.on_arrow_combo_changed)
        ec_layout.addWidget(self.arrow_combo)
        
        style_layout.addWidget(self.edge_controls)
        
        self.connect_controls = QWidget()
        cc_layout = QHBoxLayout(self.connect_controls)
        cc_layout.setContentsMargins(0,0,0,0)
        btn_connect = QPushButton("Relier les nœuds")
        btn_connect.setStyleSheet("background: #EBF8FF; border: 1px solid #90CDF4; color: #2B6CB0; font-weight: bold;")
        btn_connect.clicked.connect(self.connect_selected_nodes)
        cc_layout.addWidget(btn_connect)
        style_layout.addWidget(self.connect_controls)
        
        self.style_bar.hide()
        
        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background: rgba(255,255,255,0.95); border-radius: 8px; border: 1px solid #ddd;")
        ol_layout = QVBoxLayout(self.overlay)
        lbl = QLabel("<b>Commandes :</b><br>- Double-clic vide : Nouveau nœud<br>- Double-clic : Éditer le texte<br>- Sélect + Tab : Ajouter une branche<br>- Ctrl + Clic : Sélectionner 2 nœuds<br>- Suppr : Supprimer l'élément")
        lbl.setFont(QFont("Segoe UI", 9))
        ol_layout.addWidget(lbl)
        self.overlay.resize(230, 140)
        self.overlay.move(20, 60)

    def setup_shortcuts(self):
        self.shortcut_tab = QShortcut(QKeySequence(Qt.Key.Key_Tab), self)
        self.shortcut_tab.activated.connect(self.on_tab_pressed)
        
        self.shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.shortcut_del.activated.connect(self.delete_selected)
        
        self.shortcut_bs = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        self.shortcut_bs.activated.connect(self.delete_selected)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.style_bar.adjustSize()
        x = (self.width() - self.style_bar.width()) // 2
        y = self.height() - self.style_bar.height() - 30
        self.style_bar.move(x, y)
        self.overlay.raise_()

    def load_last_project_on_startup(self):
        last_path = self.settings.value("last_project_path", "")
        if last_path and os.path.exists(last_path):
            self.load_project_from_path(last_path)
        else:
            self.new_project(force_empty=True)
            
        QTimer.singleShot(100, self.center_on_graph)

    def center_on_graph(self):
        ws = self.current_workspace()
        if not ws: return
        rect = ws.scene.itemsBoundingRect()
        if not rect.isEmpty():
            ws.view.centerOn(rect.center())

    def close_tab(self, index) -> bool:
        ws = self.tab_widget.widget(index)
        if ws and ws.is_dirty:
            self.tab_widget.setCurrentWidget(ws)
            name = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
            reply = QMessageBox.question(
                self, 
                "Modifications non enregistrées",
                f"Le projet '{name}' a été modifié.\nVoulez-vous enregistrer les modifications avant de fermer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_project()
                if ws.is_dirty: return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            self.new_project(force_empty=True)
            self.tab_widget.removeTab(0)
        return True

    def closeEvent(self, event: QCloseEvent):
        while self.tab_widget.count() > 0:
            if not self.close_tab(0):
                event.ignore()
                return
            if self.tab_widget.count() == 1 and not self.tab_widget.widget(0).is_dirty and self.tab_widget.widget(0).current_file_path is None:
                break
        event.accept()

    def on_tab_changed(self, index):
        self.update_title()
        ws = self.current_workspace()
        if ws:
            idx = self.routing_combo.findData(ws.scene.line_routing_mode)
            if idx != -1:
                self.routing_combo.blockSignals(True)
                self.routing_combo.setCurrentIndex(idx)
                self.routing_combo.blockSignals(False)
        self.on_selection_changed()

    def update_title(self):
        ws = self.current_workspace()
        if not ws: return
        base_title = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
        suffix = " *" if ws.is_dirty else ""
        display_title = base_title + suffix
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), display_title)
        self.setWindowTitle(f"Mindy - MindMap App - {display_title}")

    def change_global_routing(self, index):
        ws = self.current_workspace()
        if not ws: return
        mode = self.routing_combo.itemData(index)
        ws.scene.line_routing_mode = mode
        
        for item in ws.scene.items():
            if isinstance(item, EdgeItem):
                item.update_position()
        ws.scene.update()
        self.save_state()

    def save_state(self):
        ws = self.current_workspace()
        if not ws or ws.is_applying_state: return
        ws.undo_stack.append(json.dumps(self.get_state()))
        ws.redo_stack.clear()
        if len(ws.undo_stack) > 41: ws.undo_stack.pop(0)
        if len(ws.undo_stack) > 1:
            ws.is_dirty = True
            self.update_title()

    def get_state(self):
        ws = self.current_workspace()
        if not ws: return {}
        
        all_items = ws.scene.items()
        nodes = [i for i in all_items if isinstance(i, NodeItem)]
        edges = [i for i in all_items if isinstance(i, EdgeItem)]
        
        root = next((n for n in nodes if n.node_id == 'root'), None) or (nodes[0] if nodes else None)
        if not root: return {}

        natural_edges = set()

        def serialize_node(node):
            data = {
                "id": node.node_id,
                "label": node.label,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "shape": node.shape_type,
                "bg": node.bg_color.name(),
                "border": node.border_color.name(),
                "font_color": node.font_color.name(),
                "border_width": node.border_width,
                "is_bold": node.is_bold,
                "status": node.status,
                "file_path": node.file_path,
                "url_link": node.url_link,
                "children": []
            }
            for edge in node.edges:
                if edge.source_node == node:
                    natural_edges.add(edge)
                    child_data = serialize_node(edge.dest_node)
                    if edge.label: child_data["edge_label"] = edge.label
                    child_data["edge_arrow_dir"] = edge.arrow_dir
                    data["children"].append(child_data)
            return data

        tree_data = serialize_node(root)
        tree_data["global_line_routing"] = ws.scene.line_routing_mode

        cross_links_data = []
        for edge in edges:
            if edge not in natural_edges:
                cross_links_data.append({
                    "from": edge.source_node.node_id,
                    "to": edge.dest_node.node_id,
                    "label": edge.label,
                    "color": edge.color.name(),
                    "arrow_dir": edge.arrow_dir
                })

        tree_data["cross_links"] = cross_links_data
        return tree_data

    def apply_state(self, state_str):
        ws = self.current_workspace()
        if not ws or not state_str.strip(): return
        
        ws.is_applying_state = True
        ws.scene.clear()
        
        try:
            root_data = json.loads(state_str)
        except Exception:
            ws.is_applying_state = False
            return

        ws.scene.line_routing_mode = root_data.get("global_line_routing", "curved")
        
        node_counter = [0]
        edge_counter = [0]
        created_nodes = {}

        def deserialize_node(data, parent_node=None):
            if not data: return None
            node_counter[0] += 1
            node_id = data.get("id") or ('root' if parent_node is None else f"node_{node_counter[0]}")
            
            x, y = data.get("x", 0.0), data.get("y", 0.0)
            bg = data.get("bg", '#60A5FA')
            border = data.get("border", '#3B82F6')
            font_color = data.get("font_color", '#ffffff')

            status = data.get("status", "none")
            raw_label = data.get("label", "")
            if status == "none" and raw_label.startswith("🚨 "):
                status = "urgent"

            # Rétrocompatibilité : Nettoyage des anciennes mentions textuelles de fichiers/liens
            clean_label = raw_label.replace("\n📄 Document joint", "").replace("\n🔗 Lien URL", "")

            node = NodeItem(
                node_id, clean_label, x, y,
                shape=data.get("shape", "box"), bg=bg, border=border, font_color=font_color,
                file_path=data.get("file_path"), url_link=data.get("url_link"), 
                is_bold=data.get("is_bold", False), status=status
            )
            node.border_width = data.get("border_width", 1)
            node.signals.itemDoubleClicked.connect(self.start_inline_editing)
            node.signals.positionChanged.connect(self.save_state)
            ws.scene.addItem(node)
            created_nodes[node_id] = node

            if parent_node:
                edge_counter[0] += 1
                edge_color = border if parent_node.node_id != 'root' else '#A0AEC0'
                edge = EdgeItem(f"edge_{edge_counter[0]}", parent_node, node, data.get("edge_label", ""), color=edge_color, arrow_dir=data.get("edge_arrow_dir", "none"))
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)

            for child_data in data.get("children", []):
                deserialize_node(child_data, node)
            return node

        deserialize_node(root_data)

        for cl in root_data.get("cross_links", []):
            source = created_nodes.get(cl["from"])
            dest = created_nodes.get(cl["to"])
            if source and dest:
                edge_counter[0] += 1
                edge = EdgeItem(f"edge_{edge_counter[0]}", source, dest, cl.get("label", ""), color=cl.get("color", "#A0AEC0"), arrow_dir=cl.get("arrow_dir", "none"))
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)

        ws.is_applying_state = False
        self.on_selection_changed()

    def undo(self):
        ws = self.current_workspace()
        if not ws or len(ws.undo_stack) <= 1: return
        ws.redo_stack.append(ws.undo_stack.pop())
        self.apply_state(ws.undo_stack[-1])
        ws.is_dirty = True
        self.update_title()

    def redo(self):
        ws = self.current_workspace()
        if not ws or not ws.redo_stack: return
        ws.undo_stack.append(ws.redo_stack.pop())
        self.apply_state(ws.undo_stack[-1])
        ws.is_dirty = True
        self.update_title()

    def on_selection_changed(self):
        ws = self.current_workspace()
        if not ws: 
            self.style_bar.hide()
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1:
            self.style_bar.show()
            self.connect_controls.hide()
            if isinstance(sel[0], NodeItem):
                self.node_controls.show()
                self.edge_controls.hide()
                has_links = bool(sel[0].file_path or sel[0].url_link)
                self.btn_open.setVisible(has_links)
                self.btn_detach.setVisible(has_links)
                
                self.shape_combo.blockSignals(True)
                self.shape_combo.setCurrentIndex(self.shape_combo.findData(sel[0].shape_type))
                self.shape_combo.blockSignals(False)
                
                self.status_combo.blockSignals(True)
                self.status_combo.setCurrentIndex(self.status_combo.findData(sel[0].status))
                self.status_combo.blockSignals(False)
                
            elif isinstance(sel[0], EdgeItem):
                self.node_controls.hide()
                self.edge_controls.show()
                
                self.arrow_combo.blockSignals(True)
                self.arrow_combo.setCurrentIndex(self.arrow_combo.findData(sel[0].arrow_dir))
                self.arrow_combo.blockSignals(False)
        elif len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            self.style_bar.show()
            self.node_controls.hide()
            self.edge_controls.hide()
            self.connect_controls.show()
        else:
            self.style_bar.hide()

    def on_shape_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            sel[0].shape_type = self.shape_combo.itemData(index)
            sel[0].recalculate_size()
            sel[0].update()
            self.save_state()

    def on_status_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            node.label = node.label.replace("🚨 ", "").replace("⏳ ", "").replace("✅ ", "")
            node.status = self.status_combo.itemData(index)
            node.recalculate_size()
            node.update()
            self.save_state()

    def on_arrow_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            sel[0].arrow_dir = self.arrow_combo.itemData(index)
            sel[0].update()
            self.save_state()

    def on_bg_double_clicked(self, pos):
        ws = self.current_workspace()
        if not ws: return
        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        if not nodes:
            node = NodeItem('root', "Nouvelle idée centrale", pos.x(), pos.y(), bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        else:
            node = NodeItem(f"node_{len(nodes)+1}", "Nouvelle idée", pos.x(), pos.y(), bg='#FFF3E0', border='#FFB74D', font_color='#333333')
            
        node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        node.signals.positionChanged.connect(self.save_state)
        ws.scene.addItem(node)
        self.save_state()

    def edit_selected_edge(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            self.start_inline_editing(sel[0])

    def start_inline_editing(self, item):
        ws = self.current_workspace()
        if not ws: return
        self.edit_item = item
        self.editor = QTextEdit(ws.view)
        
        if isinstance(item, NodeItem):
            clean_text = item.label.replace('🚨 ', '').replace('⏳ ', '').replace('✅ ', '')
            view_pos = ws.view.mapFromScene(item.pos())
            w = int(item.rect.width())
            h = max(int(item.rect.height()), 40)
            self.editor.setGeometry(view_pos.x() - w//2, view_pos.y() - h//2, w, h)
        else:
            clean_text = item.label
            center = item.path().pointAtPercent(0.5)
            view_pos = ws.view.mapFromScene(center)
            self.editor.setGeometry(view_pos.x() - 75, view_pos.y() - 15, 150, 40)

        self.editor.setText(clean_text)
        self.editor.setStyleSheet("border: 2px solid #60A5FA; background: white; font-family: Segoe UI; font-size: 11pt;")
        self.editor.selectAll()
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.editor.show()
        self.editor.setFocus()
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == getattr(self, 'editor', None):
            if event.type() == event.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.commit_edit()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.editor.deleteLater()
                    self.editor = None
                    return True
            elif event.type() == event.Type.FocusOut:
                self.commit_edit()
                return True
        return super().eventFilter(obj, event)

    def commit_edit(self):
        if not hasattr(self, 'editor') or self.editor is None: return
        new_text = self.editor.toPlainText().strip()
        
        if isinstance(self.edit_item, NodeItem):
            if new_text:
                self.edit_item.label = new_text
                self.edit_item.recalculate_size()
        else:
            self.edit_item.label = new_text
            self.edit_item.update()
            
        self.editor.deleteLater()
        self.editor = None
        self.save_state()

    def on_tab_pressed(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            self.add_child_node(sel[0])

    def delete_selected(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if not sel: return
        
        for item in sel:
            if isinstance(item, NodeItem):
                for edge in list(item.edges):
                    if edge in edge.source_node.edges: edge.source_node.edges.remove(edge)
                    if edge in edge.dest_node.edges: edge.dest_node.edges.remove(edge)
                    if edge.scene() == ws.scene: ws.scene.removeItem(edge)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
            elif isinstance(item, EdgeItem):
                if item in item.source_node.edges: item.source_node.edges.remove(item)
                if item in item.dest_node.edges: item.dest_node.edges.remove(item)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
                    
        self.save_state()

    def calculate_smart_position(self, parent_node):
        ws = self.current_workspace()
        if not ws or not parent_node:
            return 150, 0
            
        parent_right_edge = parent_node.pos().x() + (parent_node.rect.width() / 2)
        target_x = parent_right_edge + 150
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        if child_edges:
            lowest_y = parent_node.pos().y()
            for e in child_edges:
                if e.dest_node.pos().y() > lowest_y: 
                    lowest_y = e.dest_node.pos().y()
            target_y = lowest_y + 85
        else:
            target_y = parent_node.pos().y()

        overlap = True
        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        if len(all_nodes) <= 1:
            return target_x, target_y

        iterations = 0
        while overlap and iterations < 100:
            overlap = False
            iterations += 1
            for n in all_nodes:
                if n == parent_node: 
                    continue
                if abs(n.pos().x() - target_x) < 180 and abs(n.pos().y() - target_y) < 65:
                    target_y += 85
                    overlap = True
                    break
        return target_x, target_y

    def add_child_node(self, parent_node):
        ws = self.current_workspace()
        new_id = f"node_{len(ws.scene.items())}"
        
        t_x, t_y = self.calculate_smart_position(parent_node)
        bg, border, text_col, edge_col = parent_node.bg_color.name(), parent_node.border_color.name(), parent_node.font_color.name(), '#A0AEC0'
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        
        if parent_node.node_id == 'root':
            pal = BRANCH_PALETTES[len(child_edges) % len(BRANCH_PALETTES)]
            bg, border, text_col, edge_col = pal['bg'], pal['border'], pal['text'], pal['edge']
        else:
            p_edge = next((e for e in parent_node.edges if e.dest_node == parent_node), None)
            if p_edge: edge_col = p_edge.color.name()

        new_node = NodeItem(new_id, "Nouvelle sous-idée", t_x, t_y, shape='box', bg=bg, border=border, font_color=text_col)
        new_node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        new_node.signals.positionChanged.connect(self.save_state)
        
        edge = EdgeItem(f"edge_{len(ws.scene.items())}", parent_node, new_node, "", color=edge_col)
        edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
        
        ws.scene.addItem(new_node)
        ws.scene.addItem(edge)
        self.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)
        self.start_inline_editing(new_node)

    def connect_selected_nodes(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            node1, node2 = sel[0], sel[1]
            already_linked = any(
                (e.source_node == node1 and e.dest_node == node2) or 
                (e.source_node == node2 and e.dest_node == node1) 
                for e in node1.edges
            )
            if not already_linked:
                edge = EdgeItem(f"edge_{len(ws.scene.items())}", node1, node2, "", color='#A0AEC0')
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)
                self.save_state()
                ws.scene.clearSelection()
                edge.setSelected(True)

    def toggle_bold(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            node.is_bold = not node.is_bold
            node.recalculate_size()
            node.update()
            self.save_state()

    def change_color(self, bg, border):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            self.apply_color_hierarchy(sel[0], bg, border, '#333333', border)
            self.save_state()

    def apply_color_hierarchy(self, node, bg, border, text_col, edge_col):
        node.bg_color = QColor(bg)
        node.border_color = QColor(border)
        node.font_color = QColor(text_col)
        node.update()
        for edge in node.edges:
            if edge.source_node == node:
                edge.color = QColor(edge_col)
                edge.update()
                self.apply_color_hierarchy(edge.dest_node, bg, border, text_col, edge_col)

    def attach_file(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
            if path:
                node = sel[0]
                node.file_path = path
                node.recalculate_size()
                self.on_selection_changed()
                node.update()
                self.save_state()

    def attach_url(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            url, ok = QInputDialog.getText(self, "Associer une URL", "Entrez l'adresse internet :", text=node.url_link or "https://")
            if ok and url.strip():
                node.url_link = url.strip()
                node.recalculate_size()
                self.on_selection_changed()
                node.update()
                self.save_state()

    def detach_links(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            node.file_path = None
            node.url_link = None
            node.recalculate_size()
            self.on_selection_changed()
            node.update()
            self.save_state()

    def open_file(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if node.url_link: QDesktopServices.openUrl(QUrl(node.url_link))
            elif node.file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(node.file_path))

    def new_project(self, force_empty=False):
        if force_empty or QMessageBox.question(self, "Nouveau", "Créer un nouveau projet dans un nouvel onglet ?") == QMessageBox.StandardButton.Yes:
            ws = MindMapWorkspace(self)
            root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
            root.signals.itemDoubleClicked.connect(self.start_inline_editing)
            root.signals.positionChanged.connect(self.save_state)
            ws.scene.addItem(root)
            
            self.tab_widget.addTab(ws, "[Nouveau Projet]")
            self.tab_widget.setCurrentWidget(ws)
            self.save_state()
            ws.is_dirty = False 
            self.update_title()

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir", "", "JSON (*.json)")
        if path: self.load_project_from_path(path)

    def load_project_from_path(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            state_str = f.read()
            
        ws = MindMapWorkspace(self, path)
        self.tab_widget.addTab(ws, os.path.basename(path))
        self.tab_widget.setCurrentWidget(ws)
        
        self.apply_state(state_str)
        ws.undo_stack.append(state_str)
        ws.is_dirty = False
        
        self.settings.setValue("last_project_path", path)
        self.update_title()
        self.center_on_graph()

    def save_project(self, force_save_as=False):
        ws = self.current_workspace()
        if not ws: return
        
        if not ws.current_file_path or force_save_as:
            path, _ = QFileDialog.getSaveFileName(self, "Enregistrer", "ma_mindmap.json", "JSON (*.json)")
            if not path: return
            ws.current_file_path = path
            
        with open(ws.current_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_state(), f, indent=2, ensure_ascii=False)
            
        ws.is_dirty = False
        self.settings.setValue("last_project_path", ws.current_file_path)
        self.update_title()

    def apply_template(self, index):
        if index == 0: return
        ws = self.current_workspace()
        if not ws: return
        
        filename = self.template_combo.itemData(index)
        self.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(base_dir, "templates", filename)
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                state_str = data["content"] if "content" in data else json.dumps(data)
                self.apply_state(state_str)
                ws.undo_stack.clear()
                ws.redo_stack.clear()
                ws.undo_stack.append(state_str)
                ws.is_dirty = True
                self.update_title()
                self.center_on_graph()
            else:
                QMessageBox.warning(self, "Erreur", f"Fichier template introuvable :\n{template_path}")

    def export_png(self):
        ws = self.current_workspace()
        if not ws: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PNG", "ma_mindmap.png", "PNG (*.png)")
        if path:
            ws.scene.clearSelection()
            rect = ws.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            
            # Récupérer le ratio de l'écran actuel
            ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else self.devicePixelRatio()
            
            # Créer un pixmap à la taille physique (pixel réel)
            pixmap = QPixmap(int(rect.width() * ratio), int(rect.height() * ratio))
            pixmap.setDevicePixelRatio(ratio)
            pixmap.fill(QColor('#f8f9fa'))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # CRUCIAL : On adapte l'échelle du painter pour dessiner avec la haute résolution
            painter.scale(ratio, ratio)
            
            # On ajuste la zone cible pour correspondre à la taille logique (sans le ratio)
            target_rect = QRectF(0, 0, rect.width(), rect.height())
            
            ws.scene.render(painter, target=target_rect, source=rect)
            painter.end()
            pixmap.save(path, "PNG", 100)

    def export_md(self):
        ws = self.current_workspace()
        if not ws: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Markdown", "ma_mindmap.md", "Markdown (*.md)")
        if path:
            nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
            root = next((n for n in nodes if n.node_id == 'root'), nodes[0] if nodes else None)
            if not root: return
            
            output = []
            def build_tree(node, depth):
                clean_label = node.label.replace('\n', ' ')
                additions = []
                if node.file_path: additions.append(f"Fichier: {node.file_path}")
                if node.url_link: additions.append(f"URL: {node.url_link}")
                link_str = f" ({', '.join(additions)})" if additions else ""
                
                output.append(f"{'  ' * depth}- {clean_label}{link_str}")
                children = [e.dest_node for e in node.edges if e.source_node == node]
                for child in children: build_tree(child, depth + 1)
                    
            build_tree(root, 0)
            with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(output))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    sys.exit(app.exec())