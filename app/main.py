import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QSettings, QTimer
from PyQt6 import sip

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
        self.setWindowTitle(f"Mindy {APP_VERSION}")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        self._clipboard_node = None

        self.current_workspace_path = None
        self.workspace_files = []

        # Initialisation des composants métiers / logiques d'abord
        self.project_service = ProjectService(self)
        self.history_service = HistoryService(self)
        self.serializer = MindMapSerializer(self)

        # Initialisation des contrôleurs
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

        # UI Principale
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setTabBarAutoHide(False) # Optionnel, mais utile
        self.tabs.setMovable(True) # Bonus sympa tant qu'à faire !
        self.tabs.tabCloseRequested.connect(self.tabs_controller.close_tab)
        self.tabs.currentChanged.connect(self.tabs_controller.on_tab_changed)
      
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        from PyQt6.QtWidgets import QLabel
        self.lbl_workspace_status = QLabel("📂 Espace de travail : Aucun")

        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        
        # Un léger délai pour laisser l'interface s'afficher
        QTimer.singleShot(100, self.initialize_startup_session)

    def initialize_startup_session(self):
        """Décide au démarrage s'il faut charger la workspace ou le dernier projet."""
        last_workspace = self.settings.value("last_collection_path", "")
        
        if last_workspace and os.path.exists(last_workspace):
            self.workspace_controller.load_workspace(last_workspace, is_startup=True)
        else:
            self.project_service.load_last_project_on_startup()

    def current_workspace(self) -> MindMapWorkspace:
        try:
            # Utilisation de sip pour s'assurer que l'objet C++ sous-jacent de Qt n'est pas mort
            if not hasattr(self, 'tabs') or self.tabs is None or sip.isdeleted(self.tabs):
                return None
            return self.tabs.currentWidget()
        except (RuntimeError, AttributeError):
            return None
   
    def setup_ui(self):
        self.setCentralWidget(self.tabs)
        create_menus(self)
        create_toolbar(self)
        create_node_toolbar(self) # C'est ici que self.style_bar et self.overlay doivent être créés

    def setup_shortcuts(self):
        setup_app_shortcuts(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 🟢 PROTECTION : On vérifie l'existence des attributs dynamiques pour éviter le crash au démarrage
        if hasattr(self, 'style_bar') and self.style_bar is not None:
            self.reposition_style_bar()
        if hasattr(self, 'overlay') and self.overlay is not None:
            self.overlay.raise_()

    def reposition_style_bar(self):
        if hasattr(self, 'style_bar') and self.style_bar is not None:
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
        ws = self.current_workspace()
        if not ws:
            return
        current_state = self.serializer.get_state()
        self.history_service.save_state(ws, current_state)
        self.tabs_controller.update_title()

    def show_about_dialog(self):
        show_app_about_dialog(self, APP_VERSION)

    def undo(self):
        ws = self.current_workspace()
        if ws:
            previous_state = self.history_service.undo(ws)
            if previous_state:
                self.serializer.apply_state(previous_state)

    def redo(self):
        ws = self.current_workspace()
        if ws:
            next_state = self.history_service.redo(ws)
            if next_state:
                self.serializer.apply_state(next_state)
        
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    
    # Sécurité géométrique
    QTimer.singleShot(50, window.reposition_style_bar)
    sys.exit(app.exec())