# controllers/tools_controller.py
import json
import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class TabsController:
    def __init__(self, app):
        self.app = app

    def close_tab(self, index) -> bool:
        ws = self.app.tabs.widget(index)
        if ws and ws.is_dirty:
            self.app.tabs.setCurrentWidget(ws) 
            name = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
            
            reply = QMessageBox.question(
                self.app, 
                "Modifications non enregistrées",
                f"Le projet '{name}' a été modifié.\nVoulez-vous enregistrer les modifications avant de fermer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                if hasattr(self.app, 'project_service'):
                    self.app.project_service.save_project()
                elif hasattr(self.app, 'save_project'):
                    self.app.save_project()
                    
                if ws.is_dirty: return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        if self.app.tabs.count() > 1:
            self.app.tabs.removeTab(index)
        else:
            if hasattr(self.app, 'project_service'):
                self.app.project_service.new_project(force_empty=True)
            elif hasattr(self.app, 'new_project'):
                self.app.new_project(force_empty=True)
            self.app.tabs.removeTab(0)
        return True
    
    def on_tab_changed(self, index):
        self.update_title()
        ws = self.app.current_workspace()
        if ws:
            is_curved = (ws.scene.line_routing_mode == 'curved')
            self.app.btn_toggle_routing.blockSignals(True)
            self.app.btn_toggle_routing.setChecked(is_curved)
            self.app.btn_toggle_routing.blockSignals(False)
            
            if hasattr(self.app, 'routing_controller'):
                self.app.routing_controller.update_routing_button_ui()

            self.app.btn_snap.blockSignals(True)
            self.app.btn_snap.setChecked(getattr(ws.scene, 'snap_to_grid', False))
            self.app.btn_snap.blockSignals(False)
            
        if hasattr(self.app, 'on_selection_changed'):
            self.app.on_selection_changed()
            
        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.update_workspace_ui()

    def update_title(self):
        ws = self.app.current_workspace()
        if not ws: return
        base_title = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
        suffix = " *" if ws.is_dirty else ""
        display_title = base_title + suffix
        self.app.tabs.setTabText(self.app.tabs.currentIndex(), display_title) 
        
        # Ajout du nom de l'espace de travail dans le titre de la fenêtre si présent
        current_ws_path = getattr(self.app, 'current_workspace_path', None)
        if current_ws_path:
            workspace_name = os.path.basename(current_ws_path)
            self.app.setWindowTitle(f"Mindy [{workspace_name}] - {display_title}")
        else:
            self.app.setWindowTitle(f"Mindy - {display_title}")