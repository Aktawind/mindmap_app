import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QSettings, QTimer

from graphics.items import NodeItem, EdgeItem
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

APP_VERSION  = "1.0.7"

class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mindy {APP_VERSION }")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        self._clipboard_node = None

        self.current_workspace_path = None
        self.workspace_files = []

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.graph_controller = GraphController(self)
        self.style_controller = StyleController(self)
        self.attachment_controller = AttachmentController(self)
        self.export_controller = ExportController(self)
        self.workspace_controller = WorkspaceController(self)
        self.tools_controller = ToolsController(self)
        self.editing_controller = EditingController(self)

        self.project_service = ProjectService(self)
        self.history_service = HistoryService(self)
        self.serializer = MindMapSerializer(self)
      
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        self.load_last_project_on_startup()
      
        last_workspace = self.settings.value("last_collection_path", "")
        
        if last_workspace and os.path.exists(last_workspace):
            QTimer.singleShot(100, lambda: self.workspace_controller.load_workspace(last_workspace))
        else:
            self.project_service.new_project()

    def current_workspace(self) -> MindMapWorkspace:
        return self.tabs.currentWidget()
   
    def setup_ui(self):
        self.setCentralWidget(self.tabs)

        create_menus(self)
        create_toolbar(self)
        create_node_toolbar(self)

    def update_routing_button_ui(self):
        if self.btn_toggle_routing.isChecked():
            self.btn_toggle_routing.setText("Liens courbes")
        else:
            self.btn_toggle_routing.setText("Liens droits")

    def toggle_line_routing(self, checked):
        """Bascule le mode de routage des lignes en fonction de l'état du bouton."""
        ws = self.tabs.currentWidget()
        if ws and hasattr(ws, 'scene'):
            # Si coché -> 'curved' (courbe), sinon -> 'orthogonal' (lignes droites/perpendiculaires)
            ws.scene.line_routing_mode = 'curved' if checked else 'orthogonal'
            
            # Met à jour le texte et le helper du bouton
            self.update_routing_button_ui()
            
            # Force chaque ligne à recalculer son tracé
            from graphics.items import EdgeItem
            for item in ws.scene.items():
                if isinstance(item, EdgeItem):
                    item.update_position()
            
            # Rafraîchit l'affichage de la scène
            ws.scene.update()

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

    def toggle_snap_to_grid(self, checked):
        ws = self.current_workspace()
        if not ws: return
        ws.scene.snap_to_grid = checked
        if checked:
            for item in ws.scene.items():
                if isinstance(item, NodeItem):
                    x = round(item.pos().x() / 20) * 20
                    y = round(item.pos().y() / 20) * 20
                    item.setPos(x, y)
            ws.scene.update()
            self.save_state()

    def load_last_project_on_startup(self):
        last_path = self.settings.value("last_project_path", "")
        if last_path and os.path.exists(last_path):
            self.project_service.load_project_from_path(last_path)
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
        ws = self.tabs.widget(index)
        if ws and ws.is_dirty:
            self.tabs.setCurrentWidget(ws)
            name = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
            reply = QMessageBox.question(
                self, 
                "Modifications non enregistrées",
                f"Le projet '{name}' a été modifié.\nVoulez-vous enregistrer les modifications avant de fermer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.project_service.save_project()
                if ws.is_dirty: return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.new_project(force_empty=True)
            self.tabs.removeTab(0)
        return True

    def closeEvent(self, event):
        """Gère la fermeture de l'application et force la sauvegarde des onglets non enregistrés."""
        # On boucle sur tous les onglets pour vérifier s'il y a des modifications en cours
        for i in range(self.tabs.count()):
            ws = self.tabs.widget(i)
            
            # Si l'onglet a été modifié (is_dirty)
            if hasattr(ws, 'is_dirty') and ws.is_dirty:
                # On active l'onglet visuellement pour que l'utilisateur voie ce qu'il sauvegarde
                self.tabs.setCurrentIndex(i)
                
                name = ws.current_file_path if ws.current_file_path else f"Sans titre {i+1}"
                reply = QMessageBox.question(
                    self, 
                    'Enregistrer les modifications',
                    f"Le document '{os.path.basename(name)}' a été modifié.\nVoulez-vous enregistrer les modifications ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # --- CRUCIAL : On force la sauvegarde immédiate ---
                    # On appelle ta méthode de sauvegarde (ajuste le nom si elle s'appelle autrement, ex: self.save_file)
                    saved = self.project_service.save_project() 
                    
                    # Si la sauvegarde a été annulée par l'utilisateur dans le prompt de fichier, on stoppe la fermeture
                    if not saved:
                        event.ignore()
                        return
                        
                elif reply == QMessageBox.StandardButton.Cancel:
                    # L'utilisateur a cliqué sur Annuler : on stoppe complètement la fermeture
                    event.ignore()
                    return

        # Si tout est sauvegardé ou que l'utilisateur a dit "Non", on accepte la fermeture
        event.accept()

    def on_tab_changed(self, index):
        self.update_title()
        ws = self.current_workspace()
        if ws:
            is_curved = (ws.scene.line_routing_mode == 'curved')
            self.btn_toggle_routing.blockSignals(True)
            self.btn_toggle_routing.setChecked(is_curved)
            self.btn_toggle_routing.blockSignals(False)
            self.update_routing_button_ui()

            self.btn_snap.blockSignals(True)
            self.btn_snap.setChecked(getattr(ws.scene, 'snap_to_grid', False))
            self.btn_snap.blockSignals(False)
        on_selection_changed(self)
        self.workspace_controller.update_workspace_ui()

    def update_title(self):
        ws = self.current_workspace()
        if not ws: return
        base_title = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
        suffix = " *" if ws.is_dirty else ""
        display_title = base_title + suffix
        self.tabs.setTabText(self.tabs.currentIndex(), display_title)
        
        # Ajout du nom de l'espace de travail dans le titre de la fenêtre si présente
        if self.current_workspace_path:
            workspace_name = os.path.basename(self.current_workspace_path)
            self.setWindowTitle(f"Mindy [{workspace_name}] - {display_title}")
        else:
            self.setWindowTitle(f"Mindy - {display_title}")

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
        """Enregistre l'état actuel de l'espace de travail pour l'historique."""
        ws = self.current_workspace()
        if not ws:
            return
        current_state = self.serializer.get_state()
        self.history_service.save_state(ws, current_state)
        
        # On s'assure que l'étoile se met à jour dès qu'un état est enregistré
        self.update_title()



    
    def sync_workspace_ui(self, ui_state):
        if not ui_state:
            return

        self.btn_snap.blockSignals(True)
        self.btn_snap.setChecked(
            ui_state["snap_to_grid"]
        )
        self.btn_snap.blockSignals(False)

        is_curved = (
            ui_state["line_routing_mode"]
            == "curved"
        )

        self.btn_toggle_routing.blockSignals(True)
        self.btn_toggle_routing.setChecked(is_curved)
        self.btn_toggle_routing.blockSignals(False)

        on_selection_changed(self)

    def on_shape_combo_changed(self, text):
        """Délègue le changement de forme géométrique au StyleController."""
        StyleController.on_shape_combo_changed(self, text)

    def on_status_combo_changed(self, text):
        """Délègue le changement de statut au StyleController."""
        StyleController.on_status_combo_changed(self, text)

    def on_arrow_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            sel[0].arrow_dir = self.arrow_combo.itemData(index)
            sel[0].update()
            self.save_state()

    
    
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