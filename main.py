import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsPathItem, QMenu, QMenuBar, QFileDialog, 
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QComboBox, QTextEdit, QTabWidget, QInputDialog
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, 
    QAction, QKeySequence, QDesktopServices, QPixmap, QShortcut, QPainterPathStroker, QIcon
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QObject, QUrl, QSettings, QTimer

# --- PALETTES DE COULEURS ---
BRANCH_PALETTES = [
    {'bg': '#FFF3E0', 'border': '#FFB74D', 'text': '#333333', 'edge': '#FFB74D'},
    {'bg': '#E8F5E9', 'border': '#81C784', 'text': '#333333', 'edge': '#81C784'},
    {'bg': '#F3E5F5', 'border': '#CE93D8', 'text': '#333333', 'edge': '#CE93D8'},
    {'bg': '#FFEBEE', 'border': '#EF9A9A', 'text': '#333333', 'edge': '#EF9A9A'},
    {'bg': '#E0F7FA', 'border': '#4DD0E1', 'text': '#333333', 'edge': '#4DD0E1'}
]

class GraphicsSignals(QObject):
    itemDoubleClicked = pyqtSignal(object)
    selectionChanged = pyqtSignal()
    positionChanged = pyqtSignal()

class NodeItem(QGraphicsItem):
    def __init__(self, node_id, label, x, y, shape='box', bg='#60A5FA', border='#3B82F6', font_color='#ffffff', file_path=None, url_link=None, is_bold=False):
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
        lines = self.label.split('\n')
        max_width = max(fm.horizontalAdvance(line) for line in lines) if lines else 0
        total_height = fm.height() * len(lines) if lines else fm.height()
        width = max(max_width + 30, 100)
        height = max(total_height + 20, 40)
        self.rect = QRectF(-width/2, -height/2, width, height)
        self.prepareGeometryChange()

    def boundingRect(self):
        padding = self.border_width + 4
        return self.rect.adjusted(-padding, -padding, padding, padding)

    def paint(self, painter, option, widget=None):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        painter.drawRoundedRect(self.rect.translated(2, 2), 5, 5)

        pen = QPen(self.border_color, self.border_width)
        if self.isSelected():
            pen.setWidth(self.border_width + 2)
            pen.setColor(self.border_color.darker(150))
        painter.setPen(pen)
        painter.setBrush(QBrush(self.bg_color))

        # On dessine TOUJOURS un rectangle arrondi par défaut
        painter.drawRoundedRect(self.rect, 6, 6)

        painter.setPen(QPen(self.font_color))
        font = QFont('Segoe UI', 11)
        if self.is_bold:
            font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect, int(Qt.AlignmentFlag.AlignCenter), self.label)

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
    def __init__(self, edge_id, source_node, dest_node, label="", color='#A0AEC0'):
        super().__init__()
        self.edge_id = edge_id
        self.source_node = source_node
        self.dest_node = dest_node
        self.label = label
        self.color = QColor(color)
        
        self.source_node.add_edge(self)
        self.dest_node.add_edge(self)
        
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(0)
        self.signals = GraphicsSignals()
        self.update_position()

    def update_position(self):
        if not self.source_node or not self.dest_node: return
        start = self.source_node.pos()
        end = self.dest_node.pos()
        
        path = QPainterPath()
        path.moveTo(start)
        ctrl_x1 = start.x() + (end.x() - start.x()) / 2
        ctrl_y1 = start.y()
        ctrl_x2 = start.x() + (end.x() - start.x()) / 2
        ctrl_y2 = end.y()
        path.cubicTo(ctrl_x1, ctrl_y1, ctrl_x2, ctrl_y2, end.x(), end.y())
        
        self.setPath(path)

    def shape(self):
        path_stroker = QPainterPathStroker()
        path_stroker.setWidth(20) 
        return path_stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        pen = QPen(self.color, 3)
        if self.isSelected():
            pen.setColor(QColor('#4A90E2'))
            pen.setWidth(4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        if self.label:
            center = self.path().pointAtPercent(0.5)
            font = QFont('Segoe UI', 10)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(self.label)
            rect = QRectF(rect)
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
        self.resize(1500, 850)
        
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
        file_menu.addAction("📁 Nouveau projet", lambda: self.new_project())
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

        self.template_combo = QComboBox()
        self.template_combo.addItem("Choisir un template...")
        self.template_combo.addItem("🎯 Cadrage d'Idée / Projet", "cadrage_idee.json")
        self.template_combo.addItem("🔍 Résolution de Problème", "resolution_probleme.json")
        self.template_combo.addItem("⏳ Organiser son temps (Eisenhower)", "gestion_temps.json")
        self.template_combo.addItem("🧠 Brain Dump (3 parties)", "brain_dump.json")
        self.template_combo.addItem("🚀 Guide Onboarding Technique", "onboarding_technique.json")
        self.template_combo.addItem("🎨 Hub Multi-Passions", "hub_passions.json")
        self.template_combo.addItem("✈️ Organisation d'un Voyage", "organisation_voyage.json")
        self.template_combo.addItem("🗣️ Préparation Réunion/Entretien", "preparation_reunion.json")
        self.template_combo.addItem("🏁 Rétrospective de Fin de Projet", "retro_projet.json")
        self.template_combo.addItem("☀️ Daily Capsule (Point du matin)", "daily_capsule.json")
        self.template_combo.addItem("🔋 Santé Mentale & Énergie", "sante_mentale_energie.json")
        self.template_combo.addItem("🚨 Urgence Colère & Agacement", "urgence_colere.json")
        self.template_combo.setStyleSheet("margin: 2px 10px; padding: 2px 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.template_combo.currentIndexChanged.connect(self.apply_template)
        menu_bar.setCornerWidget(self.template_combo, Qt.Corner.TopRightCorner)

        self.style_bar = QFrame(self)
        self.style_bar.setStyleSheet("""
            QFrame { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }
            QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 12px; }
            QPushButton:hover { background: #e2e8f0; }
        """)
        style_layout = QHBoxLayout(self.style_bar)
        
        self.node_controls = QWidget()
        nc_layout = QHBoxLayout(self.node_controls)
        nc_layout.setContentsMargins(0,0,0,0)
        
        btn_bold = QPushButton("B")
        btn_bold.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_bold.setFixedSize(26, 26)
        btn_bold.clicked.connect(self.toggle_bold)
        nc_layout.addWidget(btn_bold)
        
        nc_layout.addWidget(self.create_separator())
        
        for color, border in [('#60A5FA', '#3B82F6'), ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'), ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')]:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background: {color}; border: 2px solid {border}; border-radius: 11px;")
            btn.clicked.connect(lambda checked, c=color, b=border: self.change_color(c, b))
            nc_layout.addWidget(btn)
            
        nc_layout.addWidget(self.create_separator())
        
        btn_urgent = QPushButton("🚨 Urgent")
        btn_urgent.setStyleSheet("background: #FFF5F5; border: 1px solid #FEB2B2; color: #C53030; font-weight: bold;")
        btn_urgent.clicked.connect(self.toggle_urgent)
        nc_layout.addWidget(btn_urgent)
        
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
        btn_edit_edge = QPushButton("📝 Nommer la relation")
        btn_edit_edge.clicked.connect(self.edit_selected_edge)
        ec_layout.addWidget(btn_edit_edge)
        style_layout.addWidget(self.edge_controls)
        
        self.connect_controls = QWidget()
        cc_layout = QHBoxLayout(self.connect_controls)
        cc_layout.setContentsMargins(0,0,0,0)
        btn_connect = QPushButton("🔗 Relier les 2 nœuds")
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
        
        self.shortcut_u = QShortcut(QKeySequence(Qt.Key.Key_U), self)
        self.shortcut_u.activated.connect(self.toggle_urgent)

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

    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            self.new_project(force_empty=True)
            self.tab_widget.removeTab(0)

    def on_tab_changed(self, index):
        self.update_title()
        self.on_selection_changed()

    def update_title(self):
        ws = self.current_workspace()
        if not ws: return
        title = "Mindy - MindMap App"
        if ws.current_file_path:
            title += f" - {os.path.basename(ws.current_file_path)}"
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(ws.current_file_path))
        else:
            title += " - [Nouveau Projet]"
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), "[Nouveau Projet]")
        self.setWindowTitle(title)

    def save_state(self):
        ws = self.current_workspace()
        if not ws or ws.is_applying_state: return
        ws.undo_stack.append(json.dumps(self.get_state()))
        ws.redo_stack.clear()
        if len(ws.undo_stack) > 41: ws.undo_stack.pop(0)

    # --- SYSTÈME DE SÉRIALISATION EN ARBRE CORRIGÉ ---
    def get_state(self):
        """ Renvoie l'arbre complet avec la liste des liens transverses """
        ws = self.current_workspace()
        if not ws: return {}
        
        all_items = ws.scene.items()
        nodes = [i for i in all_items if isinstance(i, NodeItem)]
        edges = [i for i in all_items if isinstance(i, EdgeItem)]
        
        root = next((n for n in nodes if n.node_id == 'root'), None)
        if not root and nodes:
            root = nodes[0]
        if not root:
            return {}

        # 1. On liste tous les edges "naturels" (arbre descendant) pour identifier les transverses
        natural_edges = set()

        def serialize_node(node):
            data = {
                "id": node.node_id,  # Sauvegarder l'ID est nécessaire pour mapper les cross-links
                "label": node.label,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "shape": node.shape_type,
                "bg": node.bg_color.name(),
                "border": node.border_color.name(),
                "font_color": node.font_color.name(),
                "border_width": node.border_width,
                "is_bold": node.is_bold,
                "file_path": node.file_path,
                "url_link": node.url_link,
                "children": []
            }
            for edge in node.edges:
                if edge.source_node == node:
                    # Si le fils considère ce nœud comme son parent "principal" dans la hiérarchie
                    # (pour éviter de dupliquer un nœud s'il est relié de manière transverse)
                    child_edges = edge.dest_node.edges
                    # On vérifie si c'est une relation descendante classique
                    natural_edges.add(edge)
                    child_data = serialize_node(edge.dest_node)
                    if edge.label:
                        child_data["edge_label"] = edge.label
                    data["children"].append(child_data)
            return data

        tree_data = serialize_node(root)

        # 2. On enregistre les liens manuels (ceux qui ne sont pas dans les branches naturelles)
        cross_links_data = []
        for edge in edges:
            if edge not in natural_edges:
                cross_links_data.append({
                    "from": edge.source_node.node_id,
                    "to": edge.dest_node.node_id,
                    "label": edge.label,
                    "color": edge.color.name()
                })

        tree_data["cross_links"] = cross_links_data
        return tree_data

    def apply_state(self, state_str):
        """ Reconstruit le graphique à partir de l'arbre JSON et des liens transverses """
        ws = self.current_workspace()
        if not ws or not state_str.strip(): return
        
        ws.is_applying_state = True
        ws.scene.clear()
        
        try:
            root_data = json.loads(state_str)
        except Exception:
            ws.is_applying_state = False
            return

        node_counter = [0]
        edge_counter = [0]
        created_nodes = {}  # Pour retrouver les nœuds par ID lors de la reconstruction des cross_links

        def deserialize_node(data, parent_node=None):
            if not data: return None
            
            node_counter[0] += 1
            # Conserver l'ID du JSON s'il existe (pratique pour l'édition manuelle), sinon générer
            node_id = data.get("id") or ('root' if parent_node is None else f"node_{node_counter[0]}")
            
            if "x" in data and "y" in data:
                x, y = data["x"], data["y"]
            else:
                if parent_node:
                    x, y = self.calculate_smart_position(ws, parent_node)
                else:
                    x, y = 0.0, 0.0

            bg = data.get("bg")
            border = data.get("border")
            font_color = data.get("font_color")
            
            if parent_node and (not bg or not border):
                bg = bg or parent_node.bg_color.name()
                border = border or parent_node.border_color.name()
                font_color = font_color or parent_node.font_color.name()
            else:
                bg = bg or '#60A5FA'
                border = border or '#3B82F6'
                font_color = font_color or '#ffffff'

            node = NodeItem(
                node_id, data["label"], x, y,
                shape=data.get("shape", "box"), bg=bg, border=border, font_color=font_color,
                file_path=data.get("file_path"), url_link=data.get("url_link"), is_bold=data.get("is_bold", False)
            )
            node.border_width = data.get("border_width", 1)
            node.signals.itemDoubleClicked.connect(self.start_inline_editing)
            node.signals.positionChanged.connect(self.save_state)
            ws.scene.addItem(node)
            
            created_nodes[node_id] = node

            if parent_node:
                edge_counter[0] += 1
                edge_id = f"edge_{edge_counter[0]}"
                edge_color = border if parent_node.node_id != 'root' else '#A0AEC0'
                edge = EdgeItem(edge_id, parent_node, node, data.get("edge_label", ""), color=edge_color)
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)

            for child_data in data.get("children", []):
                deserialize_node(child_data, node)
                
            return node

        # Reconstruire l'arbre
        deserialize_node(root_data)

        # Reconstruire les liens transverses ("cross_links") s'il y en a
        for cl in root_data.get("cross_links", []):
            source = created_nodes.get(cl["from"])
            dest = created_nodes.get(cl["to"])
            if source and dest:
                edge_counter[0] += 1
                edge_id = f"edge_{edge_counter[0]}"
                edge = EdgeItem(edge_id, source, dest, cl.get("label", ""), color=cl.get("color", "#A0AEC0"))
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)

        ws.is_applying_state = False
        self.on_selection_changed()

    def undo(self):
        ws = self.current_workspace()
        if not ws or len(ws.undo_stack) <= 1: return
        ws.redo_stack.append(ws.undo_stack.pop())
        self.apply_state(ws.undo_stack[-1])

    def redo(self):
        ws = self.current_workspace()
        if not ws or not ws.redo_stack: return
        ws.undo_stack.append(ws.redo_stack.pop())
        self.apply_state(ws.undo_stack[-1])

    # --- INTERACTIONS GRAPHIQUES ---
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
            elif isinstance(sel[0], EdgeItem):
                self.node_controls.hide()
                self.edge_controls.show()
        elif len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            self.style_bar.show()
            self.node_controls.hide()
            self.edge_controls.hide()
            self.connect_controls.show()
        else:
            self.style_bar.hide()

    def on_bg_double_clicked(self, pos):
        ws = self.current_workspace()
        if not ws: return
        # S'il n'y a aucun noeud, on crée la racine
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
            clean_text = item.label.replace('\n📄 Document joint', '').replace('🚨 ', '')
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
    
    def reposition_children_rec(self, parent_node):
        """ Repositionne récursivement les enfants pour éviter les chevauchements dus à la taille du texte """
        ws = self.current_workspace()
        if not ws: return

        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        if not child_edges:
            return

        # Calcul de la position X de départ pour les enfants (marge à droite du parent)
        parent_right_edge = parent_node.pos().x() + (parent_node.rect.width() / 2)
        target_x = parent_right_edge + 120  # 120 pixels d'espace constant

        # On aligne ou distribue verticalement les enfants
        first_child_y = parent_node.pos().y()
        
        for i, edge in enumerate(child_edges):
            child = edge.dest_node
            # On propage le X calculé
            child.setPos(target_x, child.pos().y() if i > 0 else first_child_y)
            
            # S'il y a plusieurs enfants, on s'assures qu'ils ne se marchent pas dessus verticalement
            if i > 0:
                prev_child = child_edges[i-1].dest_node
                prev_bottom = prev_child.pos().y() + (prev_child.rect.height() / 2)
                current_top_target = prev_bottom + 40 + (child.rect.height() / 2) # 40px d'espace vertical
                if child.pos().y() < current_top_target:
                    child.setPos(child.pos().x(), current_top_target)
            
            # On met à jour l'alignement de la ligne d'attache
            edge.update_position()
            
            # On applique la règle récursivement aux enfants de cet enfant
            self.reposition_children_rec(child)

    def commit_edit(self):
        if not hasattr(self, 'editor') or self.editor is None: return
        new_text = self.editor.toPlainText().strip()
        
        if isinstance(self.edit_item, NodeItem):
            if new_text:
                if self.edit_item.label.startswith("🚨 "): new_text = "🚨 " + new_text
                if self.edit_item.file_path: new_text += "\n📄 Document joint"
                self.edit_item.label = new_text
                self.edit_item.recalculate_size()
                
                # --- REPOSITIONNEMENT DYNAMIQUE APRÈS ÉDITION ---
                self.reposition_children_rec(self.edit_item)
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
                    if edge in edge.source_node.edges:
                        edge.source_node.edges.remove(edge)
                    if edge in edge.dest_node.edges:
                        edge.dest_node.edges.remove(edge)
                    if edge.scene() == ws.scene:
                        ws.scene.removeItem(edge)
                if item.scene() == ws.scene:
                    ws.scene.removeItem(item)
            elif isinstance(item, EdgeItem):
                if item in item.source_node.edges:
                    item.source_node.edges.remove(item)
                if item in item.dest_node.edges:
                    item.dest_node.edges.remove(item)
                if item.scene() == ws.scene:
                    ws.scene.removeItem(item)
                    
        self.save_state()

    def calculate_smart_position(self, ws, parent_node):
        # On démarre du bord droit réel du nœud parent
        parent_right_edge = parent_node.pos().x() + (parent_node.rect.width() / 2)
        target_x = parent_right_edge + 120
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        
        if child_edges:
            lowest_y = parent_node.pos().y()
            for e in child_edges:
                if e.dest_node.pos().y() > lowest_y:
                    lowest_y = e.dest_node.pos().y()
            target_y = lowest_y + 75
        else:
            target_y = parent_node.pos().y()

        overlap = True
        # On cherche uniquement les nœuds présents dans le workspace (ws) actuel
        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        while overlap:
            overlap = False
            for n in all_nodes:
                if abs(n.pos().x() - target_x) < 160 and abs(n.pos().y() - target_y) < 55:
                    target_y += 75
                    overlap = True
                    break
                    
        return target_x, target_y

    def add_child_node(self, parent_node):
        ws = self.current_workspace()
        new_id = f"node_{len(ws.scene.items())}"
        edge_id = f"edge_{len(ws.scene.items())}"
        
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
        
        edge = EdgeItem(edge_id, parent_node, new_node, "", color=edge_col)
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
                edge_id = f"edge_{len(ws.scene.items())}"
                edge = EdgeItem(edge_id, node1, node2, "", color='#A0AEC0')
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

    def toggle_urgent(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if node.label.startswith("🚨 "):
                node.label = node.label.replace("🚨 ", "")
                node.border_color = QColor(node.bg_color).darker(120)
                node.border_width = 1
            else:
                node.label = "🚨 " + node.label
                node.border_color = QColor("#E53E3E")
                node.border_width = 3
            node.recalculate_size()
            self.save_state()

    def attach_file(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
            if path:
                node = sel[0]
                node.file_path = path
                if "📄 Document joint" not in node.label:
                    node.label += "\n📄 Document joint"
                node.recalculate_size()
                self.on_selection_changed()
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
            node.label = node.label.replace("\n📄 Document joint", "")
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
            if node.url_link:
                QDesktopServices.openUrl(QUrl(node.url_link))
            elif node.file_path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(node.file_path))

    # --- LOGIQUE PROJETS & FICHIERS ---
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
            self.update_title()

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir", "", "JSON (*.json)")
        if path:
            self.load_project_from_path(path)

    def load_project_from_path(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            state_str = f.read()
            
        ws = MindMapWorkspace(self, path)
        self.tab_widget.addTab(ws, os.path.basename(path))
        self.tab_widget.setCurrentWidget(ws)
        
        self.apply_state(state_str)
        self.save_state()
        
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
            
        self.settings.setValue("last_project_path", ws.current_file_path)
        self.update_title()

    def apply_template(self, index):
        if index == 0: return
        ws = self.current_workspace()
        if not ws: return
        
        filename = self.template_combo.itemData(index)
        self.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            template_path = os.path.join(base_dir, "templates", filename)
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                state_str = data["content"] if "content" in data else json.dumps(data)
                self.apply_state(state_str)
                ws.undo_stack.clear()
                ws.redo_stack.clear()
                self.save_state()
                self.center_on_graph()
            else:
                QMessageBox.warning(self, "Erreur", f"Le fichier template est introuvable :\n{template_path}")

    def export_png(self):
        ws = self.current_workspace()
        if not ws: return
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PNG", "ma_mindmap.png", "PNG (*.png)")
        if path:
            ws.scene.clearSelection()
            rect = ws.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            pixmap = QPixmap(int(rect.width()), int(rect.height()))
            pixmap.fill(QColor('#f8f9fa'))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            ws.scene.render(painter, target=QRectF(pixmap.rect()), source=rect)
            painter.end()
            pixmap.save(path)

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
                clean_label = node.label.replace('\n📄 Document joint', '').replace('\n', ' ')
                additions = []
                if node.file_path: additions.append(f"Fichier: {node.file_path}")
                if node.url_link: additions.append(f"URL: {node.url_link}")
                link_str = f" ({', '.join(additions)})" if additions else ""
                
                output.append(f"{'  ' * depth}- {clean_label}{link_str}")
                children = [e.dest_node for e in node.edges if e.source_node == node]
                for child in children:
                    build_tree(child, depth + 1)
                    
            build_tree(root, 0)
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(output))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    sys.exit(app.exec())