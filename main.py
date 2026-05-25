import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsPathItem, QMenu, QMenuBar, QFileDialog, 
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QComboBox, QTextEdit
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, 
    QAction, QKeySequence, QDesktopServices, QPixmap, QShortcut, QPainterPathStroker
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QObject, QUrl

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
    def __init__(self, node_id, label, x, y, shape='box', bg='#60A5FA', border='#3B82F6', font_color='#ffffff', file_path=None):
        super().__init__()
        self.node_id = node_id
        self.label = label
        self.shape_type = shape
        self.bg_color = QColor(bg)
        self.border_color = QColor(border)
        self.font_color = QColor(font_color)
        self.file_path = file_path
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

        if self.shape_type == 'ellipse':
            painter.drawEllipse(self.rect)
        else:
            painter.drawRoundedRect(self.rect, 6, 6)

        painter.setPen(QPen(self.font_color))
        painter.setFont(QFont('Segoe UI', 11))
        # Utilisation stricte de l'Enum AlignmentFlag pour éviter les erreurs PyQt
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
            # Correction du bug ici : Passage correct du rectangle et de l'alignement
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


class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mindy - MindMap App - [Nouveau Projet]")
        self.resize(1500, 850)
        
        self.current_file_path = None
        self.undo_stack = []
        self.redo_stack = []
        self.is_applying_state = False

        self.setup_ui()
        self.setup_shortcuts()
        self.new_project(force_empty=True)

    def create_separator(self):
        sep = QWidget()
        sep.setFixedSize(2, 22)
        sep.setStyleSheet("background-color: #cbd5e1; margin: 0 4px;")
        return sep

    def setup_ui(self):
        self.scene = MindMapScene(self)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.scene.signals.itemDoubleClicked.connect(self.on_bg_double_clicked)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet("border: none;")
        self.setCentralWidget(self.view)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Fichier")
        file_menu.addAction("📁 Nouveau projet", self.new_project)
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
        
        btn_rect = QPushButton("Rectangle")
        btn_rect.clicked.connect(lambda: self.change_shape('box'))
        nc_layout.addWidget(btn_rect)
        
        btn_oval = QPushButton("Ovale")
        btn_oval.clicked.connect(lambda: self.change_shape('ellipse'))
        nc_layout.addWidget(btn_oval)

        nc_layout.addWidget(self.create_separator())
        
        btn_attach = QPushButton("📎 Associer")
        btn_attach.clicked.connect(self.attach_file)
        nc_layout.addWidget(btn_attach)
        
        self.btn_open = QPushButton("📂 Ouvrir")
        self.btn_open.setStyleSheet("background: #2D3748; color: white;")
        self.btn_open.clicked.connect(self.open_file)
        nc_layout.addWidget(self.btn_open)

        self.btn_detach = QPushButton("❌ Dissocier")
        self.btn_detach.setStyleSheet("background: #FED7D7; color: #C53030;")
        self.btn_detach.clicked.connect(self.detach_file)
        nc_layout.addWidget(self.btn_detach)
        
        style_layout.addWidget(self.node_controls)
        
        self.edge_controls = QWidget()
        ec_layout = QHBoxLayout(self.edge_controls)
        ec_layout.setContentsMargins(0,0,0,0)
        btn_edit_edge = QPushButton("📝 Nommer la relation")
        btn_edit_edge.clicked.connect(self.edit_selected_edge)
        ec_layout.addWidget(btn_edit_edge)
        style_layout.addWidget(self.edge_controls)
        
        self.style_bar.hide()
        
        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background: rgba(255,255,255,0.95); border-radius: 8px; border: 1px solid #ddd;")
        ol_layout = QVBoxLayout(self.overlay)
        lbl = QLabel("<b>Commandes :</b><br>- Double-clic vide : Nouveau nœud<br>- Double-clic : Éditer le texte<br>- Sélect + Tab : Ajouter une branche<br>- Suppr : Supprimer l'élément")
        lbl.setFont(QFont("Segoe UI", 9))
        ol_layout.addWidget(lbl)
        self.overlay.resize(230, 130)
        self.overlay.move(20, 40)

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

    # --- HISTORIQUE & ETATS ---
    def get_state(self):
        nodes, edges = [], []
        for item in self.scene.items():
            if isinstance(item, NodeItem):
                nodes.append({
                    'id': item.node_id, 'label': item.label, 'x': item.pos().x(), 'y': item.pos().y(),
                    'shape': item.shape_type, 'bg': item.bg_color.name(), 'border': item.border_color.name(),
                    'font_color': item.font_color.name(), 'border_width': item.border_width, 'file_path': item.file_path
                })
            elif isinstance(item, EdgeItem):
                edges.append({
                    'id': item.edge_id, 'from': item.source_node.node_id, 'to': item.dest_node.node_id,
                    'label': item.label, 'color': item.color.name()
                })
        return {'nodes': nodes, 'edges': edges}

    def save_state(self):
        if self.is_applying_state: return
        self.undo_stack.append(json.dumps(self.get_state()))
        self.redo_stack.clear()
        if len(self.undo_stack) > 41: self.undo_stack.pop(0)

    def apply_state(self, state_str):
        self.is_applying_state = True
        state = json.loads(state_str)
        self.scene.clear()
        
        node_map = {}
        for nd in state['nodes']:
            bg = nd.get('bg')
            border = nd.get('border')
            font_color = nd.get('font_color')
            
            if not bg and 'color' in nd:
                color_data = nd['color']
                if isinstance(color_data, dict):
                    bg = color_data.get('background', '#60A5FA')
                    border = color_data.get('border', '#3B82F6')
                else:
                    bg = border = color_data
                    
            if not font_color and 'font' in nd:
                font_data = nd['font']
                if isinstance(font_data, dict):
                    font_color = font_data.get('color', '#ffffff')
            
            bg = bg or '#60A5FA'
            border = border or '#3B82F6'
            font_color = font_color or '#ffffff'

            node = NodeItem(nd['id'], nd['label'], nd['x'], nd['y'], nd['shape'], bg, border, font_color, nd.get('file_path'))
            node.border_width = nd.get('border_width', 1)
            node.signals.itemDoubleClicked.connect(self.start_inline_editing)
            node.signals.positionChanged.connect(self.save_state)
            self.scene.addItem(node)
            node_map[nd['id']] = node
            
        for ed in state['edges']:
            if ed['from'] in node_map and ed['to'] in node_map:
                color = ed.get('color', '#A0AEC0')
                if isinstance(color, dict):
                    color = color.get('color', '#A0AEC0')
                
                edge = EdgeItem(ed['id'], node_map[ed['from']], node_map[ed['to']], ed.get('label', ''), color)
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                self.scene.addItem(edge)
                
        self.is_applying_state = False
        self.on_selection_changed()

    def undo(self):
        if len(self.undo_stack) <= 1: return
        self.redo_stack.append(self.undo_stack.pop())
        self.apply_state(self.undo_stack[-1])

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(self.redo_stack.pop())
        self.apply_state(self.undo_stack[-1])

    # --- INTERACTIONS GRAPHIQUES ---
    def on_selection_changed(self):
        sel = self.scene.selectedItems()
        if len(sel) == 1:
            self.style_bar.show()
            if isinstance(sel[0], NodeItem):
                self.node_controls.show()
                self.edge_controls.hide()
                has_file = bool(sel[0].file_path)
                self.btn_open.setVisible(has_file)
                self.btn_detach.setVisible(has_file)
            elif isinstance(sel[0], EdgeItem):
                self.node_controls.hide()
                self.edge_controls.show()
        else:
            self.style_bar.hide()

    def on_bg_double_clicked(self, pos):
        node_id = f"node_{len(self.scene.items())}"
        node = NodeItem(node_id, "Nouvelle idée", pos.x(), pos.y(), bg='#FFF3E0', border='#FFB74D', font_color='#333333')
        node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        node.signals.positionChanged.connect(self.save_state)
        self.scene.addItem(node)
        self.save_state()

    def edit_selected_edge(self):
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            self.start_inline_editing(sel[0])

    def start_inline_editing(self, item):
        self.edit_item = item
        self.editor = QTextEdit(self.view)
        
        if isinstance(item, NodeItem):
            clean_text = item.label.replace('\n📄 Document joint', '').replace('🚨 ', '')
            view_pos = self.view.mapFromScene(item.pos())
            w = int(item.rect.width())
            h = max(int(item.rect.height()), 40)
            self.editor.setGeometry(view_pos.x() - w//2, view_pos.y() - h//2, w, h)
        else:
            clean_text = item.label
            center = item.path().pointAtPercent(0.5)
            view_pos = self.view.mapFromScene(center)
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
                if self.edit_item.label.startswith("🚨 "): new_text = "🚨 " + new_text
                if self.edit_item.file_path: new_text += "\n📄 Document joint"
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
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            self.add_child_node(sel[0])

    def delete_selected(self):
        """ Suppression avec nettoyage strict des liaisons en mémoire """
        if hasattr(self, 'editor') and self.editor is not None: return
        sel = self.scene.selectedItems()
        if not sel: return
        
        for item in sel:
            if isinstance(item, NodeItem):
                for edge in list(item.edges):
                    # Supprime le lien des listes internes des deux noeuds connectés
                    if edge in edge.source_node.edges:
                        edge.source_node.edges.remove(edge)
                    if edge in edge.dest_node.edges:
                        edge.dest_node.edges.remove(edge)
                    if edge.scene() == self.scene:
                        self.scene.removeItem(edge)
                if item.scene() == self.scene:
                    self.scene.removeItem(item)
            elif isinstance(item, EdgeItem):
                if item in item.source_node.edges:
                    item.source_node.edges.remove(item)
                if item in item.dest_node.edges:
                    item.dest_node.edges.remove(item)
                if item.scene() == self.scene:
                    self.scene.removeItem(item)
                    
        self.save_state()

    def calculate_smart_position(self, parent_node):
        """ Algorithme robuste anti-chevauchement calqué sur l'original web """
        target_x = parent_node.pos().x() + 220
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
        all_nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
        
        while overlap:
            overlap = False
            for n in all_nodes:
                if abs(n.pos().x() - target_x) < 160 and abs(n.pos().y() - target_y) < 55:
                    target_y += 75
                    overlap = True
                    break
                    
        return target_x, target_y

    def add_child_node(self, parent_node):
        new_id = f"node_{len(self.scene.items())}"
        edge_id = f"edge_{len(self.scene.items())}"
        
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
        
        self.scene.addItem(new_node)
        self.scene.addItem(edge)
        self.save_state()
        
        self.scene.clearSelection()
        new_node.setSelected(True)
        self.start_inline_editing(new_node)

    # --- STYLES & PIECES JOINTES ---
    def change_color(self, bg, border):
        sel = self.scene.selectedItems()
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

    def change_shape(self, shape_type):
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            sel[0].shape_type = shape_type
            sel[0].update()
            self.save_state()

    def toggle_urgent(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        sel = self.scene.selectedItems()
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
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier")
            if path:
                node = sel[0]
                node.file_path = path
                if "📄 Document joint" not in node.label:
                    node.label += "\n📄 Document joint"
                node.recalculate_size()
                self.btn_open.setVisible(True)
                self.btn_detach.setVisible(True)
                self.save_state()

    def detach_file(self):
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem) and sel[0].file_path:
            node = sel[0]
            node.file_path = None
            node.label = node.label.replace("\n📄 Document joint", "")
            node.recalculate_size()
            self.btn_open.setVisible(False)
            self.btn_detach.setVisible(False)
            self.save_state()

    def open_file(self):
        sel = self.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem) and sel[0].file_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(sel[0].file_path))

    # --- FICHIERS & EXPORTS ---
    def update_title(self):
        title = "Mindy - MindMap App"
        if self.current_file_path:
            title += f" - {os.path.basename(self.current_file_path)}"
        else:
            title += " - [Nouveau Projet]"
        self.setWindowTitle(title)

    def new_project(self, force_empty=False):
        if force_empty or QMessageBox.question(self, "Nouveau", "Créer un nouveau projet ? Les modifications non enregistrées seront perdues.") == QMessageBox.StandardButton.Yes:
            self.scene.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.current_file_path = None
            
            root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
            root.signals.itemDoubleClicked.connect(self.start_inline_editing)
            root.signals.positionChanged.connect(self.save_state)
            self.scene.addItem(root)
            self.save_state()
            self.update_title()
            self.on_selection_changed()

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir", "", "JSON (*.json)")
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                state_str = f.read()
            self.apply_state(state_str)
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.save_state()
            self.current_file_path = path
            self.update_title()

    def save_project(self, force_save_as=False):
        if not self.current_file_path or force_save_as:
            path, _ = QFileDialog.getSaveFileName(self, "Enregistrer", "ma_mindmap.json", "JSON (*.json)")
            if not path: return
            self.current_file_path = path
            
        with open(self.current_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_state(), f, indent=2)
        self.update_title()

    def apply_template(self, index):
        if index == 0: return
        filename = self.template_combo.itemData(index)
        self.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self, "Template", "Charger ce template remplacera la mind map actuelle. Continuer ?") == QMessageBox.StandardButton.Yes:
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            template_path = os.path.join(base_dir, "templates", filename)
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if "content" in data:
                    state_str = data["content"]
                else:
                    state_str = json.dumps(data)
                    
                self.apply_state(state_str)
                self.undo_stack.clear()
                self.redo_stack.clear()
                self.current_file_path = None
                self.save_state()
                self.update_title()
            else:
                QMessageBox.warning(self, "Erreur", f"Le fichier template est introuvable :\n{template_path}")

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PNG", "ma_mindmap.png", "PNG (*.png)")
        if path:
            self.scene.clearSelection()
            rect = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            pixmap = QPixmap(int(rect.width()), int(rect.height()))
            pixmap.fill(QColor('#f8f9fa'))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, target=QRectF(pixmap.rect()), source=rect)
            painter.end()
            pixmap.save(path)

    def export_md(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Markdown", "ma_mindmap.md", "Markdown (*.md)")
        if path:
            nodes = [i for i in self.scene.items() if isinstance(i, NodeItem)]
            root = next((n for n in nodes if n.node_id == 'root'), nodes[0] if nodes else None)
            if not root: return
            
            output = []
            def build_tree(node, depth):
                clean_label = node.label.replace('\n📄 Document joint', '').replace('\n', ' ')
                link = f" (Lien: {node.file_path})" if node.file_path else ""
                output.append(f"{'  ' * depth}- {clean_label}{link}")
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