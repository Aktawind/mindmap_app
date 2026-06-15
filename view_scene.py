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
        # On importe EdgeItem pour vérifier si l'élément supprimé est une branche
        from items import EdgeItem
        
        if isinstance(item, EdgeItem):
            # 1. On nettoie proprement les connexions de la branche dans les nœuds
            if item.source_node and item in item.source_node.edges:
                item.source_node.edges.remove(item)
            if item.dest_node and item in item.dest_node.edges:
                item.dest_node.edges.remove(item)
            
            # 2. On marque le workspace comme modifié pour activer la sauvegarde
            if hasattr(self, 'parent_workspace') and self.parent_workspace:
                self.parent_workspace.is_dirty = True
            elif hasattr(self, 'parent') and callable(self.parent) and self.parent():
                # Selon comment est lié ton parent, on remonte jusqu'au MindMapWorkspace
                ws = self.parent()
                if hasattr(ws, 'is_dirty'):
                    ws.is_dirty = True

        # On appelle la méthode d'origine de Qt pour réellement enlever l'élément de la scène
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

        # --- CORRECTION ICI ---
        self._moved_nodes_start_positions = {}
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, 'scene') and self.scene():
            # 1. On récupère d'abord l'élément qui se trouve directement sous le curseur
            clicked_item = self.itemAt(event.position().toPoint())
            
            # Si l'élément sous le curseur fait partie d'un ensemble (ex: un sous-élément graphique),
            # on remonte jusqu'à l'élément principal (le NodeItem)
            while clicked_item and clicked_item.parentItem():
                clicked_item = clicked_item.parentItem()
            
            if clicked_item:
                self._moved_nodes_start_positions[clicked_item] = clicked_item.pos()

            # 2. On ajoute aussi les autres éléments qui étaient déjà sélectionnés (pour la multi-sélection)
            for item in self.scene().selectedItems():
                self._moved_nodes_start_positions[item] = item.pos()

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

        # Appeler d'abord le comportement par défaut de Qt pour 
        # que le déplacement des items soit appliqué et finalisé
        super().mouseReleaseEvent(event)

        # --- AJOUT : Vérifier si au moins un nœud a changé de position ---
        has_moved = False
        if hasattr(self, '_moved_nodes_start_positions'):
            for item, start_pos in self._moved_nodes_start_positions.items():
                # On compare la position de départ à la position actuelle
                # Si l'item existe toujours dans la scène et a bougé
                if item.scene() and item.pos() != start_pos:
                    has_moved = True
                    break
            # Nettoyage de la variable temporaire
            del self._moved_nodes_start_positions

        # On ne sauvegarde QUE si un mouvement réel a été détecté
        if has_moved and hasattr(self, 'scene') and self.scene():
            workspace = getattr(self.scene(), 'parent_workspace', None)
            if workspace and hasattr(workspace, 'main_app'):
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
        
        self.scene.selectionChanged.connect(self.main_app.on_selection_changed)
        self.scene.signals.itemDoubleClicked.connect(self.main_app.on_bg_double_clicked)
        
        self.view = MindMapControlView(self.scene, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.centerOn(0, 0)


    def auto_center_root(self):      
        self.view.centerOn(0, 0)