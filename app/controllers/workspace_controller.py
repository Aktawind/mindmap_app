import json
import os

from PyQt6.QtWidgets import QMessageBox, QFileDialog

class WorkspaceController:
    def __init__(self, app):
        self.app = app
        self.current_workspace_path = None
        self.workspace_files = []

    def new_workspace(self):
        """ Crée un nouveau fichier de workspace vide et nettoie l'espace """
        # CORRECTION : Le parent du QFileDialog est self.app, pas self
        path, _ = QFileDialog.getSaveFileName(self.app, "Créer une nouvelle workspace", "MaSessionDuMatin.mindy", "workspace Mindy (*.mindy)")
        if not path:
            return

        self.current_workspace_path = path
        self.workspace_files = []

        # Nettoyage propre des onglets actuels
        self.app.tabs.blockSignals(True)
        try:
            self.app.tabs.clear()
        finally:
            self.app.tabs.blockSignals(False)

        self.app.project_service.new_project() # Ouvre un premier onglet vierge
        self.auto_save_workspace()
        self.app.update_title()

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
            # CORRECTION : Le parent de QMessageBox est self.app
            QMessageBox.critical(self.app, "Erreur Sauvegarde", f"Impossible de mettre à jour la workspace :\n{str(e)}")

    def update_workspace_ui(self):
        """ Met à jour le texte de la barre d'outils pour afficher la workspace active """
        if self.current_workspace_path:
            name = os.path.basename(self.current_workspace_path)
            count = len(self.workspace_files)
            self.app.lbl_workspace_status.setText(f"📁 Workspace :  {name} ({count} carte{'s' if count > 1 else ''})")
        else:
            # CORRECTION : Remplacement de self.lbl_workspace_status par self.app.lbl_workspace_status
            self.app.lbl_workspace_status.setText("📁 Workspace : Aucun")

    def load_workspace(self, path=None):
        """ Charge une workspace (soit via explorateur si path=None, soit directement au démarrage) """
        if not path:
            # CORRECTION : Le parent de QFileDialog est self.app
            path, _ = QFileDialog.getOpenFileName(self.app, "Ouvrir un Espace de travail", "", "Espace Mindy (*.mindy)")
            if not path:
                return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_paths = data.get("files", [])

            # Bloquer les signaux pour vider proprement les onglets actuels
            self.app.tabs.blockSignals(True)
            try:
                self.app.tabs.clear()
            finally:
                self.app.tabs.blockSignals(False)

            self.current_workspace_path = path
            self.workspace_files = []

            # Charger uniquement les fichiers JSON valides sur le disque
            for f_path in file_paths:
                if os.path.exists(f_path):
                    self.app.project_service.load_project_from_path(f_path)
                    self.workspace_files.append(f_path)

            # Si le fichier .mindy était vide, on crée un onglet vierge par défaut
            if not self.workspace_files:
                self.app.project_service.new_project()

            self.update_workspace_ui()
            self.app.update_title()

        except Exception as e:
            QMessageBox.critical(self.app, "Erreur", f"Impossible de charger l'espace de travail :\n{str(e)}")

    def add_current_tab_to_workspace(self):
        """ Ajoute la carte active à la playlist et sauvegarde immédiatement """
        if not self.current_workspace_path:
            QMessageBox.warning(self.app, "Attention", "Veuillez d'abord ouvrir ou créer une workspace avec les boutons de gauche.")
            return

        ws = self.app.current_workspace()
        if not ws: return

        if not ws.current_file_path:
            QMessageBox.warning(self.app, "Action requise", "Sauvegardez d'abord ce fichier JSON sur votre disque (Ctrl+S) avant de l'ajouter.")
            return

        if ws.current_file_path in self.workspace_files:
            QMessageBox.information(self.app, "Information", "Cette carte est déjà incluse dans la workspace.")
            return

        self.workspace_files.append(ws.current_file_path)
        self.auto_save_workspace() 

    def remove_current_tab_from_workspace(self):
        """ Enlève la carte active de la workspace (sans fermer l'onglet) """
        if not self.current_workspace_path:
            return

        ws = self.app.app.current_workspace() if hasattr(self.app, 'app') else self.app.current_workspace()
        if not ws or not ws.current_file_path: 
            return

        if ws.current_file_path in self.workspace_files:
            self.workspace_files.remove(ws.current_file_path)
            self.auto_save_workspace() 
        else:
            QMessageBox.warning(self.app, "Action impossible", "Ce fichier ne fait pas partie de la workspace.")