# controllers/tools_controller.py
import json
import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class ToolsController:

    @staticmethod
    def resource_path(relative_path):
        """Calcule le chemin absolu vers les ressources (gère l'exécutable PyInstaller)."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            # __file__ étant dans app/controllers/, on remonte au besoin vers le dossier parent
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def create_separator(parent_toolbar):
        """Crée un séparateur visuel personnalisé pour la barre d'outils."""
        sep = QWidget(parent_toolbar)
        sep.setFixedSize(2, 22)
        sep.setStyleSheet("background-color: #cbd5e1; margin: 0 4px;")
        return sep
       
    @staticmethod
    def apply_template(app, index):
        """Applique un fichier template JSON à la mind map courante."""
        if index == 0: return
        ws = app.current_workspace()
        if not ws: return
        
        filename = app.template_combo.itemData(index)
        app.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(app, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            # Recherche du fichier dans le dossier 'templates' global
            template_path = ToolsController.resource_path(os.path.join("templates", filename))
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    state_str = data["content"] if "content" in data else json.dumps(data)
                    app.apply_state(state_str)
                    
                    ws.undo_stack.clear()
                    if hasattr(ws, 'redo_stack'):
                        ws.redo_stack.clear()
                        
                    ws.undo_stack.append(state_str)
                    ws.is_dirty = True
                    app.update_title()
                    app.center_on_graph()
                except Exception as e:
                    QMessageBox.critical(app, "Erreur", f"Erreur lors de la lecture du template :\n{str(e)}")
            else:
                QMessageBox.warning(app, "Erreur", f"Fichier template introuvable :\n{template_path}")