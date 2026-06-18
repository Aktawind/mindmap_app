# services/project_service.py
import json
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from graphics.items import NodeItem
from services.serializer import MindMapSerializer
from controllers.workspace_controller import WorkspaceController
from graphics.scene import MindMapWorkspace

class ProjectService:
    @staticmethod
    def new_project(self, force_empty=False):
        ws = MindMapWorkspace(self)
        root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        root.signals.itemDoubleClicked.connect(self.start_inline_editing)
        root.signals.positionChanged.connect(self.save_state)
        ws.scene.addItem(root)
        
        self.tabs.addTab(ws, "[Nouveau Projet]")
        self.tabs.setCurrentWidget(ws)
        self.save_state()
        ws.is_dirty = False 
        self.update_title()

    def load_project(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ouvrir un ou plusieurs projets", "", "JSON (*.json)")
        if paths:
            for path in paths:
                self.load_project_from_path(path)

    def load_project_from_path(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            state_str = f.read()
            
        ws = MindMapWorkspace(self, path)
        self.tabs.addTab(ws, os.path.basename(path))
        self.tabs.setCurrentWidget(ws)
        
        self.apply_state(state_str)
        ws.undo_stack.append(state_str)
        ws.is_dirty = False
        
        self.settings.setValue("last_project_path", path)
        self.update_title()
        self.center_on_graph()

    def save_project(self, force_save_as=False):
        ws = self.current_workspace()
        if not ws: return False
        
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
                self, 
                "Enregistrer la carte", 
                f"{default_name}.json", 
                "Mind Map Files (*.json)"
            )
            if not path: return False
            ws.current_file_path = path
            
        with open(ws.current_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_state(), f, indent=2, ensure_ascii=False)
            
        ws.is_dirty = False
        self.settings.setValue("last_project_path", ws.current_file_path)
        self.update_title()
        return True