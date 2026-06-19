import json
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout
from signals import GraphicsSignals
from graphics.items import NodeItem, EdgeItem
from ui.selection_manager import on_selection_changed

class MindMapScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor('#f8f9fa'))
        self.signals = GraphicsSignals()
        self.line_routing_mode = 'curved'
        self.snap_to_grid = False
        self.parent_workspace = None

    def mouseDoubleClickEvent(self, event):
        # Utilisation de la vue principale pour mapper l'élément sous le curseur de façon stable
        views = self.views()
        item = views[0].itemAt(views[0].mapFromScene(event.scenePos())) if views else None
        
        if not item:
            self.signals.itemDoubleClicked.emit(event.scenePos())
        super().mouseDoubleClickEvent(event)

    def removeItem(self, item):
        from graphics.items import EdgeItem, NodeItem
        
        # 1. Gestion si l'item supprimé est une Ligne/Branche
        if isinstance(item, EdgeItem):
            if item.source_node and item in getattr(item.source_node, 'edges', []):
                item.source_node.edges.remove(item)
            if item.dest_node and item in getattr(item.dest_node, 'edges', []):
                item.dest_node.edges.remove(item)
                
        # 2. Gestion de sécurité si l'item supprimé est un Nœud (Nettoyage en cascade des lignes associées)
        elif isinstance(item, NodeItem):
            if hasattr(item, 'edges'):
                for edge in list(item.edges):
                    if edge in self.items():
                        self.removeItem(edge)

        # 3. Notification de modification au workspace parent
        ws = getattr(self, 'parent_workspace', None)
        if not ws and hasattr(self, 'parent') and callable(self.parent):
            ws = self.parent()
            
        if ws and hasattr(ws, 'is_dirty'):
            ws.is_dirty = True

        super().removeItem(item)


class MindMapControlView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setStyleSheet("border: none;")
        
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._moved_nodes_start_positions = {}

    def mousePressEvent(self, event):
        # 🚨 FIX GÉOMÉTRIQUE : Extraction des coordonnées relatives strictes au Viewport de Qt
        viewport_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()

        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(viewport_pos)
            if not item:
                self._is_panning = True
                self._pan_start_x = viewport_pos.x()
                self._pan_start_y = viewport_pos.y()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return

        self._moved_nodes_start_positions = {}
        if event.button() == Qt.MouseButton.LeftButton and self.scene():
            clicked_item = self.itemAt(viewport_pos)
            
            # Remontée récursive vers le NodeItem racine en cas de clic sur un sous-composant textuel
            while clicked_item and clicked_item.parentItem():
                clicked_item = clicked_item.parentItem()
            
            if clicked_item:
                self._moved_nodes_start_positions[clicked_item] = clicked_item.pos()

            for item in self.scene().selectedItems():
                self._moved_nodes_start_positions[item] = item.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        viewport_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        
        if self._is_panning:
            dx = viewport_pos.x() - self._pan_start_x
            dy = viewport_pos.y() - self._pan_start_y
            
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(dx))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(dy))
            
            self._pan_start_x = viewport_pos.x()
            self._pan_start_y = viewport_pos.y()
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

        has_moved = False
        if hasattr(self, '_moved_nodes_start_positions') and self._moved_nodes_start_positions:
            for item, start_pos in self._moved_nodes_start_positions.items():
                try:
                    if item.scene() and item.pos() != start_pos:
                        has_moved = True
                        break
                except RuntimeError:
                    # Sécurité si l'item a été supprimé à la volée pendant le déplacement
                    continue
            self._moved_nodes_start_positions.clear()

        if has_moved and self.scene():
            workspace = getattr(self.scene(), 'parent_workspace', None)
            if workspace and getattr(workspace, 'main_app', None):
                if hasattr(workspace.main_app, 'save_state'):
                    workspace.main_app.save_state()

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
        self.scene.parent_workspace = self
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)

        self.scene.selectionChanged.connect(lambda: on_selection_changed(self.main_app))
        
        if hasattr(self.main_app, 'tools_controller'):
            self.scene.signals.itemDoubleClicked.connect(self.main_app.tools_controller.on_bg_double_clicked)
        
        self.view = MindMapControlView(self.scene, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.centerOn(0, 0)

    def auto_center_root(self):      
        self.view.centerOn(0, 0)