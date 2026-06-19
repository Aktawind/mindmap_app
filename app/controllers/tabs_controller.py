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
        """Ferme un onglet spécifié avec vérification des modifications non enregistrées."""
        if index < 0 or index >= self.app.tabs.count():
            return False
            
        ws = self.app.tabs.widget(index)
        if ws and getattr(ws, 'is_dirty', False):
            # On force le focus sur l'onglet concerné pour que l'utilisateur voie ce qu'il va fermer
            self.app.tabs.setCurrentWidget(ws) 
            name = os.path.basename(ws.current_file_path) if getattr(ws, 'current_file_path', None) else "[Nouveau Projet]"
            
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
                    
                # Si après tentative d'enregistrement l'espace est toujours dirty 
                # (ex: l'utilisateur a fait "Annuler" dans le QFileDialog de sauvegarde), on annule la fermeture
                if getattr(ws, 'is_dirty', False): 
                    return False
                    
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        # Procédure de suppression de l'onglet sécurisée
        if self.app.tabs.count() > 1:
            self.app.tabs.removeTab(index)
        else:
            # S'il ne reste qu'un seul onglet, on en crée un nouveau propre avant de supprimer l'ancien
            if hasattr(self.app, 'project_service'):
                self.app.project_service.new_project(force_empty=True)
            elif hasattr(self.app, 'new_project'):
                self.app.new_project(force_empty=True)
            self.app.tabs.removeTab(0)
            
        return True
    
    def on_tab_changed(self, index):
        """Met à jour l'ensemble de l'interface graphique lors du passage d'un onglet à un autre."""
        if index < 0: return
        
        self.update_title()
        ws = self.app.current_workspace()
        if not ws: return
        
        # 1. Synchronisation sécurisée du mode de routage des lignes
        if hasattr(ws, 'scene') and ws.scene is not None:
            current_mode = getattr(ws.scene, 'line_routing_mode', 'curved')
            is_curved = (current_mode == 'curved')
            
            if hasattr(self.app, 'btn_toggle_routing') and self.app.btn_toggle_routing is not None:
                self.app.btn_toggle_routing.blockSignals(True)
                self.app.btn_toggle_routing.setChecked(is_curved)
                self.app.btn_toggle_routing.blockSignals(False)
                
                if hasattr(self.app, 'routing_controller'):
                    self.app.routing_controller.update_routing_button_ui()

            # 2. Synchronisation sécurisée de l'aimant de la grille
            if hasattr(self.app, 'btn_snap') and self.app.btn_snap is not None:
                self.app.btn_snap.blockSignals(True)
                self.app.btn_snap.setChecked(getattr(ws.scene, 'snap_to_grid', False))
                self.app.btn_snap.blockSignals(False)
            
        # 3. Notification des autres contrôleurs dépendants
        if hasattr(self.app, 'on_selection_changed'):
            self.app.on_selection_changed()
            
        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.update_workspace_ui()

    def update_title(self):
        """Actualise dynamiquement le titre de l'onglet et de la fenêtre principale."""
        ws = self.app.current_workspace()
        if not ws: return
        
        idx = self.app.tabs.currentIndex()
        if idx < 0: return

        base_title = os.path.basename(ws.current_file_path) if getattr(ws, 'current_file_path', None) else "[Nouveau Projet]"
        suffix = " *" if getattr(ws, 'is_dirty', False) else ""
        display_title = base_title + suffix
        
        self.app.tabs.setTabText(idx, display_title) 
        
        current_ws_path = getattr(self.app, 'current_workspace_path', None)
        if current_ws_path:
            workspace_name = os.path.basename(current_ws_path)
            self.app.setWindowTitle(f"Mindy [{workspace_name}] - {display_title}")
        else:
            self.app.setWindowTitle(f"Mindy - {display_title}")