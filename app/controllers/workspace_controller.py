import json
import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from ui.selection_manager import on_selection_changed

class WorkspaceController:
    def __init__(self, app):
        self.app = app
        self.current_workspace_path = None
        self.workspace_files = []

    def _check_and_close_existing_tabs(self) -> bool:
        """Ferme proprement tous les onglets ouverts en demandant de sauvegarder."""
        if not hasattr(self.app, 'tabs_controller') or not hasattr(self.app, 'tabs'):
            return True
            
        # On ferme à l'envers en utilisant notre contrôleur validé
        for i in range(self.app.tabs.count() - 1, -1, -1):
            success = self.app.tabs_controller.close_tab(i)
            if not success:
                return False  # L'utilisateur a cliqué sur Annuler, on stoppe tout
        return True

    def new_workspace(self):
        """ Crée un nouveau fichier de workspace vide et nettoie l'espace si validé """
        # Sécurité : on refuse de créer si l'utilisateur refuse de sauvegarder l'état actuel
        if not self._check_and_close_existing_tabs():
            return

        path, _ = QFileDialog.getSaveFileName(
            self.app, 
            "Créer une nouvelle workspace", 
            "MaSessionDuMatin.mindy", 
            "workspace Mindy (*.mindy)"
        )
        if not path:
            return

        self.current_workspace_path = path
        self.app.settings.setValue(
            "last_collection_path",
            path
        )
        self.app.settings.sync()
        self.workspace_files = []

        # Nettoyage propre des onglets actuels (ils ont déjà été sauvés au-dessus)
        self.app.tabs.blockSignals(True)
        try:
            self.app.tabs.clear()
        finally:
            self.app.tabs.blockSignals(False)

        if hasattr(self.app, 'project_service'):
            self.app.project_service.new_project() # Ouvre un premier onglet vierge
            
        self.auto_save_workspace()
        if hasattr(self.app, 'tabs_controller'):
            self.app.tabs_controller.update_title()

    def auto_save_workspace(self):
        """ Écrit instantanément les modifications dans le fichier .mindy """
        if not self.current_workspace_path:
            return
        
        data = {
            "version": "1.0",
            "files": self.workspace_files
        }
        try:
            with open(self.current_workspace_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.update_workspace_ui()
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur Sauvegarde", f"Impossible de mettre à jour la workspace :\n{str(e)}")

    def update_workspace_ui(self):
        """ Met à jour le texte de la barre d'outils pour afficher la workspace active """
        if not hasattr(self.app, 'lbl_workspace_status') or self.app.lbl_workspace_status is None:
            return

        if self.current_workspace_path:
            name = os.path.basename(self.current_workspace_path)
            count = len(self.workspace_files)
            self.app.lbl_workspace_status.setText(f"📁 Workspace :  {name} ({count} carte{'s' if count > 1 else ''})")
        else:
            self.app.lbl_workspace_status.setText("📁 Workspace : Aucun")

    def load_workspace(self, path=None, is_startup=False):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self.app, "Ouvrir un Espace de travail", "", "Espace Mindy (*.mindy)")
            if not path:
                return

        if not is_startup:
            if not self._check_and_close_existing_tabs():
                return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 🟢 1. On définit le chemin AVANT toute manipulation
            self.current_workspace_path = path
            self.app.settings.setValue(
                "last_collection_path",
                path
            )
            self.app.settings.sync()
            file_paths = data.get("files", [])

            self.app.tabs.blockSignals(True)
            try:
                self.app.tabs.clear()
            finally:
                self.app.tabs.blockSignals(False)

            self.workspace_files = []

            if hasattr(self.app, 'project_service'):
                for f_path in file_paths:
                    if os.path.exists(f_path):
                        self.app.project_service.load_project_from_path(f_path)
                        self.workspace_files.append(f_path)

                if not self.workspace_files:
                    self.app.project_service.new_project()

            # 🟢 2. On force une mise à jour explicite de l'UI maintenant que tout est prêt
            self.update_workspace_ui() 
            
            if hasattr(self.app, 'tabs_controller'):
                self.app.tabs_controller.update_title()

        except Exception as e:
            QMessageBox.critical(self.app, "Erreur", f"Impossible de charger l'espace de travail :\n{str(e)}")

    def add_current_tab_to_workspace(self):
        """ Ajoute la carte active à la playlist et sauvegarde immédiatement """
        if not self.current_workspace_path:
            QMessageBox.warning(self.app, "Attention", "Veuillez d'abord ouvrir ou créer une workspace avec les boutons de gauche.")
            return

        ws = self.app.current_workspace()
        if not ws: return

        file_path = getattr(ws, 'current_file_path', None)
        if not file_path:
            QMessageBox.warning(self.app, "Action requise", "Sauvegardez d'abord ce fichier JSON sur votre disque (Ctrl+S) avant de l'ajouter.")
            return

        if file_path in self.workspace_files:
            QMessageBox.information(self.app, "Information", "Cette carte est déjà incluse dans la workspace.")
            return

        self.workspace_files.append(file_path)
        self.auto_save_workspace() 

    def remove_current_tab_from_workspace(self):
        """ Enlève la carte active de la workspace (et ferme proprement l'onglet associé) """
        if not self.current_workspace_path:
            return

        ws = self.app.current_workspace()
        if not ws: return
        
        file_path = getattr(ws, 'current_file_path', None)
        if not file_path: 
            return

        if file_path in self.workspace_files:
            self.workspace_files.remove(file_path)
            self.auto_save_workspace()
            
            idx = self.app.tabs.currentIndex()
            if idx >= 0:
                self.app.tabs_controller.close_tab(idx)
        else:
            QMessageBox.warning(self.app, "Action impossible", "Ce fichier ne fait pas partie de la workspace.")

    def sync_workspace_ui(self, ui_state):
        if not ui_state:
            return

        if hasattr(self.app, 'btn_snap') and self.app.btn_snap:
            self.app.btn_snap.blockSignals(True)
            self.app.btn_snap.setChecked(ui_state.get("snap_to_grid", False))
            self.app.btn_snap.blockSignals(False)

        if hasattr(self.app, 'routing_mode_combo') and self.app.routing_mode_combo:
            combo = self.app.routing_mode_combo
            mode = ui_state.get("line_routing_mode", "curved")
            combo.blockSignals(True)
            index = combo.findData(mode)
            if index < 0:
                index = combo.findData("curved")  # fallback sécurité
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)

        if hasattr(self.app, 'on_selection_changed'):
            self.app.on_selection_changed()

    def center_on_graph(self):
        ws = self.app.current_workspace()
        if not ws: return
        rect = ws.scene.itemsBoundingRect()
        if not rect.isEmpty():
            ws.view.centerOn(rect.center())