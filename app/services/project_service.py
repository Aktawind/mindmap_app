import json
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from graphics.items import NodeItem
from graphics.scene import MindMapWorkspace
from PyQt6.QtCore import QSettings, QTimer

class ProjectService:
    def __init__(self, app):
        self.app = app

    def new_project(self, force_empty=False):
        # 1. On crée une NOUVELLE instance de workspace pour cet onglet
        ws = MindMapWorkspace(self.app)
        
        # 2. On configure le nœud racine
        root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        
        root.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        ws.scene.addItem(root)
        
        # 3. Ajout de l'onglet
        self.app.tabs.addTab(ws, "[Nouveau Projet]")
        self.app.tabs.setCurrentWidget(ws)
        
        self.app.save_state()
        ws.is_dirty = False 
        self.app.tabs_controller.update_title()

    def load_project(self):
        paths, _ = QFileDialog.getOpenFileNames(self.app, "Ouvrir un ou plusieurs projets", "", "JSON (*.json)")
        if paths:
            for path in paths:
                self.load_project_from_path(path)

    def load_project_from_path(self, path):
        if not os.path.exists(path):
            return

        with open(path, 'r', encoding='utf-8') as f:
            state_str = f.read()
            
        # 1. On crée une NOUVELLE instance dédiée à ce fichier
        ws = MindMapWorkspace(self.app)
        ws.current_file_path = path
        
        # 2. On l'ajoute aux onglets avant d'appliquer l'état (pour que l'UI soit prête)
        self.app.tabs.addTab(ws, os.path.basename(path))
        self.app.tabs.setCurrentWidget(ws)
        
        # 3. On applique les données de la mindmap et on initialise son historique
        self.app.serializer.apply_state(state_str)
        
        if hasattr(ws, 'undo_stack'):
            ws.undo_stack.append(state_str)
            
        ws.is_dirty = False
        
        # 4. Finalisation de l'affichage
        self.app.settings.setValue("last_project_path", path)
        self.app.tabs_controller.update_title()
        self.app.workspace_controller.center_on_graph()

    def save_project(self, force_save_as=False):
        ws = self.app.current_workspace()
        if not ws: 
            return False
        
        if not ws.current_file_path or force_save_as:
            nodes = [item for item in ws.scene.items() if isinstance(item, NodeItem)]
            root_node = next((n for n in nodes if n.node_id == 'root'), None)
            if root_node and root_node.label:
                default_name = root_node.label.replace('\n', ' ').strip()
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    default_name = default_name.replace(char, '')
                if not default_name:
                    default_name = "ma_mindmap"
            else:
                default_name = "ma_mindmap"

            path, _ = QFileDialog.getSaveFileName(
                self.app, 
                "Enregistrer la carte", 
                f"{default_name}.json", 
                "Mind Map Files (*.json)"
            )
            if not path: 
                return False
            ws.current_file_path = path
            
        try:
            with open(ws.current_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.app.serializer.get_state(), f, indent=2, ensure_ascii=False)
                
            ws.is_dirty = False
            self.app.settings.setValue("last_project_path", ws.current_file_path)
            self.app.tabs_controller.update_title()
            return True
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur Sauvegarde", f"Impossible de sauvegarder le fichier :\n{str(e)}")
            return False
        
    def load_last_project_on_startup(self):
        last_path = self.app.settings.value("last_project_path", "")
        if last_path and os.path.exists(last_path):
            self.load_project_from_path(last_path)
        else:
            self.new_project(force_empty=True)
            
        QTimer.singleShot(100, self.app.workspace_controller.center_on_graph)