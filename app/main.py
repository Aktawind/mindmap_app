import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QSettings, QTimer

from graphics.scene import MindMapWorkspace

from ui.menus import create_menus
from ui.toolbar import create_toolbar
from ui.shortcuts import setup_app_shortcuts
from ui.about_dialog import show_app_about_dialog
from ui.node_toolbar import create_node_toolbar
from ui.selection_manager import on_selection_changed

from services.serializer import MindMapSerializer
from services.history_service import HistoryService
from services.project_service import ProjectService

from controllers.editing_controller import EditingController
from controllers.graph_controller import GraphController
from controllers.style_controller import StyleController
from controllers.attachment_controller import AttachmentController
from controllers.export_controller import ExportController
from controllers.workspace_controller import WorkspaceController
from controllers.tools_controller import ToolsController
from controllers.routing_controller import RoutingController
from controllers.grid_controller import GridController
from controllers.tabs_controller import TabsController

APP_VERSION  = "1.0.7"

class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mindy {APP_VERSION }")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        self._clipboard_node = None

        self.current_workspace_path = None
        self.workspace_files = []

        self.graph_controller = GraphController(self)
        self.style_controller = StyleController(self)
        self.attachment_controller = AttachmentController(self)
        self.export_controller = ExportController(self)
        self.workspace_controller = WorkspaceController(self)
        self.tools_controller = ToolsController(self)
        self.editing_controller = EditingController(self)
        self.grid_controller = GridController(self)
        self.routing_controller = RoutingController(self)
        self.tabs_controller = TabsController(self)

        self.project_service = ProjectService(self)
        self.history_service = HistoryService(self)
        self.serializer = MindMapSerializer(self)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs_controller.close_tab)
        self.tabs.currentChanged.connect(self.tabs_controller.on_tab_changed)
      
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        self.project_service.load_last_project_on_startup()
      
        last_workspace = self.settings.value("last_collection_path", "")
        
        if last_workspace and os.path.exists(last_workspace):
            QTimer.singleShot(100, lambda: self.workspace_controller.load_workspace(last_workspace))
        else:
            self.project_service.new_project()

    def current_workspace(self) -> MindMapWorkspace:
        try:
            if not hasattr(self, 'tabs') or self.tabs is None:
                return None
            # On vérifie avec une méthode native que l'objet C++ sous-jacent n'est pas mort
            if self.tabs.parent() is None and not self.isVisible(): 
                return None # L'application est probablement en train de fermer
                
            return self.tabs.currentWidget()
        except (RuntimeError, AttributeError):
            # Si Qt lève une exception "wrapped C/C++ object has been deleted", on la passe sous silence
            return None
   
    def setup_ui(self):
        self.setCentralWidget(self.tabs)

        create_menus(self)
        create_toolbar(self)
        create_node_toolbar(self)

    def setup_shortcuts(self):
        setup_app_shortcuts(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reposition_style_bar()
        self.overlay.raise_()

    def reposition_style_bar(self):
        self.style_bar.adjustSize()
        x = (self.width() - self.style_bar.width()) // 2
        y = self.height() - self.style_bar.height() - 30
        self.style_bar.move(x, y)

    def closeEvent(self, event):
        if hasattr(self, 'tools_controller'):
            self.tools_controller.handle_close_event(event)
        else:
            event.accept()

    def save_state(self):
        """Enregistre l'état actuel de l'espace de travail pour l'historique."""
        ws = self.current_workspace()
        if not ws:
            return
        current_state = self.serializer.get_state()
        self.history_service.save_state(ws, current_state)
        
        # On s'assure que l'étoile se met à jour dès qu'un état est enregistré
        self.tabs_controller.update_title()

    def show_about_dialog(self):
        show_app_about_dialog(self, APP_VERSION)

    def undo(self):
        previous_state = self.history_service.undo(self.current_workspace())
        if previous_state:
            self.serializer.apply_state(previous_state)

    def redo(self):
        next_state = self.history_service.redo(self.current_workspace())
        if next_state:
            self.serializer.apply_state(next_state)
        
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    # Forcer la mise à jour géométrique initiale de la barre de boutons dès l'affichage
    QTimer.singleShot(50, window.reposition_style_bar)
    sys.exit(app.exec())