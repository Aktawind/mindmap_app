import json
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget, QVBoxLayout
from PyQt6.QtGui import QPainter
from signals import GraphicsSignals
from items import NodeItem, EdgeItem

class MindMapScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor('#f8f9fa'))
        self.signals = GraphicsSignals()
        self.line_routing_mode = 'curved'
        self.snap_to_grid = False

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if not item:
            self.signals.itemDoubleClicked.emit(event.scenePos())
        super().mouseDoubleClickEvent(event)

    def removeItem(self, item):
        # On importe les classes localement pour éviter les imports circulaires
        from items import EdgeItem, NodeItem
        
        # CAS 1 : Si l'élément qu'on est en train de supprimer est un NŒUD
        if isinstance(item, NodeItem):
            # On doit détruire TOUTES les branches connectées à ce nœud d'abord.
            # On utilise list(item.edges) pour faire une copie propre de la liste pendant qu'on la vide.
            for edge in list(item.edges):
                if edge.scene() == self:
                    self.removeItem(edge) # On appelle récursivement removeItem pour chaque branche
            
            # On prévient le Workspace que le mind map a changé
            if hasattr(self, 'parent_workspace') and self.parent_workspace:
                self.parent_workspace.is_dirty = True
                # On force la mise à jour visuelle du titre de l'application (pour afficher l'astérisque *)
                if hasattr(self.parent_workspace, 'main_app') and self.parent_workspace.main_app:
                    self.parent_workspace.main_app.update_title()

        # CAS 2 : Si l'élément qu'on est en train de supprimer est une BRANCHE (Edge)
        elif isinstance(item, EdgeItem):
            # 1. On nettoie proprement les pointeurs dans les nœuds source et destination
            if item.source_node and item in item.source_node.edges:
                item.source_node.edges.remove(item)
            if item.dest_node and item in item.dest_node.edges:
                item.dest_node.edges.remove(item)
            
            # 2. On prévient le Workspace et on met à jour le titre (*)
            if hasattr(self, 'parent_workspace') and self.parent_workspace:
                self.parent_workspace.is_dirty = True
                if hasattr(self.parent_workspace, 'main_app') and self.parent_workspace.main_app:
                    self.parent_workspace.main_app.update_title()

        # ENFIN : On appelle la méthode d'origine de PyQt pour retirer physiquement l'élément de la scène
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
        self.scene.parent_workspace = self
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        
        self.scene.selectionChanged.connect(self.main_app.on_selection_changed)
        self.scene.signals.itemDoubleClicked.connect(self.main_app.on_bg_double_clicked)
        
        self.view = MindMapControlView(self.scene, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.centerOn(0, 0)
