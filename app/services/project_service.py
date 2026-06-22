import json
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from graphics.items import NodeItem
from graphics.scene import MindMapWorkspace
from PyQt6.QtCore import QTimer

class ProjectService:
    def __init__(self, app):
        self.app = app

    def new_project(self, force_empty=False):
        """Crée une nouvelle instance de workspace et l'initialise avec un nœud racine."""
        ws = MindMapWorkspace(self.app)
        
        root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        
        if hasattr(self.app, 'editing_controller'):
            root.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        ws.scene.addItem(root)
        
        # Ajout sécurisé à l'UI
        self.app.tabs.addTab(ws, "[Nouveau Projet]")
        self.app.tabs.setCurrentWidget(ws)

        if hasattr(self.app, 'routing_controller'):
            self.app.routing_controller.update_routing_button_ui()
        
        # Enregistrement du premier état dans l'historique (au format dict !)
        if hasattr(self.app, 'save_state'):
            self.app.save_state()
            
        ws.is_dirty = False 
        if hasattr(self.app, 'tabs_controller'):
            self.app.tabs_controller.update_title()

    def load_project(self):
        """Ouvre un explorateur pour charger plusieurs fichiers simultanément."""
        paths, _ = QFileDialog.getOpenFileNames(self.app, "Ouvrir un ou plusieurs projets", "", "JSON (*.json)")
        if paths:
            for path in paths:
                self.load_project_from_path(path)

    def load_project_from_path(self, path):
        """Instancie un onglet à partir d'un chemin de fichier .json valide."""
        if not os.path.exists(path):
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                # 🚨 ALIGNEMENT : On décode immédiatement en dictionnaire pour harmoniser les types
                state_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur Lecture", f"Fichier JSON corrompu ou illisible :\n{str(e)}")
            return
            
        ws = MindMapWorkspace(self.app)
        ws.current_file_path = path
        
        self.app.tabs.addTab(ws, os.path.basename(path))
        self.app.tabs.setCurrentWidget(ws)

        if hasattr(self.app, 'routing_controller'):
            self.app.routing_controller.update_routing_button_ui()
        
        # Application de l'état décodé
        if hasattr(self.app, 'serializer'):
            self.app.serializer.apply_state(state_data)
        
        # 🚨 FIX CRITIQUE : L'état initial poussé dans le undo_stack est bien un dictionnaire copiavel
        if hasattr(ws, 'undo_stack'):
            import copy
            ws.undo_stack.append(copy.deepcopy(state_data))
            
        ws.is_dirty = False
        
        if hasattr(self.app, 'settings'):
            self.app.settings.setValue("last_project_path", path)
            
        if hasattr(self.app, 'tabs_controller'):
            self.app.tabs_controller.update_title()

        # 🟢 APPEL DE LA FONCTION DE NETTOYAGE :
        # Exécuté après que la scène a été entièrement reconstruite (apply_state)
        if hasattr(self.app, 'attachment_controller'):
            self.app.attachment_controller.clean_orphan_attachments()
            
        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.center_on_graph()

    def save_project(self, force_save_as=False):
        """Sauvegarde le projet courant. Génère automatiquement un nom propre si Save As."""
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
            if hasattr(self.app, 'serializer'):
                state_to_save = self.app.serializer.get_state()
                with open(ws.current_file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_to_save, f, indent=2, ensure_ascii=False)
                
            ws.is_dirty = False
            
            if hasattr(self.app, 'settings'):
                self.app.settings.setValue("last_project_path", ws.current_file_path)
                
            if hasattr(self.app, 'tabs_controller'):
                self.app.tabs_controller.update_title()
            return True
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur Sauvegarde", f"Impossible de sauvegarder le fichier :\n{str(e)}")
            return False
        
    def load_last_project_on_startup(self):
        """Procédure de démarrage : recharge la dernière session ou ouvre un canevas vierge."""
        last_path = ""
        if hasattr(self.app, 'settings'):
            last_path = self.app.settings.value("last_project_path", "")
            
        if last_path and os.path.exists(last_path):
            self.load_project_from_path(last_path)
        else:
            self.new_project(force_empty=True)
            
        if hasattr(self.app, 'workspace_controller'):
            QTimer.singleShot(100, self.app.workspace_controller.center_on_graph)