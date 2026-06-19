import json
import os
import sys
import time
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class ToolsController:
    def __init__(self, app):
        self.app = app
        # 🚨 FIX : Initialisation obligatoire du presse-papier interne pour éviter le AttributeError
        self._clipboard_node = None

    @staticmethod
    def resource_path(relative_path):
        """Calcule le chemin absolu vers les ressources (gère l'exécutable PyInstaller)."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            # Remonte proprement vers le dossier racine de l'application
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def create_separator(parent_toolbar):
        """Crée un séparateur visuel personnalisé pour la barre d'outils."""
        sep = QWidget(parent_toolbar)
        sep.setFixedSize(2, 22)
        sep.setStyleSheet("background-color: #cbd5e1; margin: 0 4px;")
        return sep
       
    def apply_template(self, index):
        """Applique un fichier template JSON à la mind map courante."""
        if index == 0: return
        ws = self.app.current_workspace()
        if not ws: return
        
        if not hasattr(self.app, 'template_combo') or self.app.template_combo is None: return
        
        filename = self.app.template_combo.itemData(index)
        self.app.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self.app, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            template_path = ToolsController.resource_path(os.path.join("templates", filename))
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    state_str = data["content"] if "content" in data else json.dumps(data)
                    
                    if hasattr(self.app, 'serializer') and self.app.serializer:
                        self.app.serializer.apply_state(state_str)
                    
                    # Nettoyage et initialisation sécurisée de l'historique d'annulation
                    if hasattr(ws, 'undo_stack'): ws.undo_stack.clear()
                    if hasattr(ws, 'redo_stack'): ws.redo_stack.clear()
                    
                    ws.undo_stack.append(state_str)
                    ws.is_dirty = True
                    
                    if hasattr(self.app, 'tabs_controller'):
                        self.app.tabs_controller.update_title()
                    if hasattr(self.app, 'workspace_controller'):
                        self.app.workspace_controller.center_on_graph()
                except Exception as e:
                    QMessageBox.critical(self.app, "Erreur", f"Erreur lors de la lecture du template :\n{str(e)}")
            else:
                QMessageBox.warning(self.app, "Erreur", f"Fichier template introuvable :\n{template_path}")

    def copy_selected(self):
        """Copie le nœud sélectionné dans le presse-papier interne."""
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            src = sel[0]
            self._clipboard_node = {
                "label": getattr(src, 'label', ''),
                "shape": getattr(src, 'shape_type', 'box'),
                "bg": src.bg_color.name() if hasattr(src, 'bg_color') else '#60A5FA',
                "border": src.border_color.name() if hasattr(src, 'border_color') else '#3B82F6',
                "font_color": src.font_color.name() if hasattr(src, 'font_color') else '#ffffff',
                "is_bold": getattr(src, 'is_bold', False),
                "status": getattr(src, 'status', 'none'),
                "notes": getattr(src, 'notes', ''),
                "file_path": getattr(src, 'file_path', None),
                "url_link": getattr(src, 'url_link', None)
            }

    def paste_node(self):
        """Colle le nœud stocké à l'emplacement central de la vue courante."""
        ws = self.app.current_workspace()
        if not ws or not self._clipboard_node: return
        
        data = self._clipboard_node
        
        # 🚨 FIX ANTI-COLLISION : ID basé sur un horodatage milliseconde pour garantir l'unicité stricte
        new_id = f"node_paste_{int(time.time() * 1000)}"
        
        center = ws.view.mapToScene(ws.view.viewport().rect().center())
        x, y = center.x(), center.y()
        
        if getattr(ws.scene, 'snap_to_grid', False):
            x = round(x / 20) * 20
            y = round(y / 20) * 20

        new_node = NodeItem(
            new_id, data["label"], x, y,
            shape=data["shape"], bg=data["bg"], border=data["border"], font_color=data["font_color"]
        )
        new_node.is_bold = data["is_bold"]
        new_node.status = data["status"]
        if hasattr(new_node, 'notes'): new_node.notes = data["notes"]
        new_node.file_path = data["file_path"]
        new_node.url_link = data["url_link"]
        
        # Liaison dynamique vers le gestionnaire d'édition textuelle
        if hasattr(self.app, 'editing_controller') and self.app.editing_controller:
            new_node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        elif hasattr(self.app, 'start_inline_editing'):
            new_node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
        
        ws.scene.addItem(new_node)
        
        if hasattr(self.app, 'save_state'):
            self.app.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)

    def auto_center_clicked(self):
        """Centre précisément la vue sur le nœud racine principal ('root')."""
        ws = self.app.current_workspace()
        if ws:
            all_items = ws.scene.items()
            root_node = next((item for item in all_items if hasattr(item, 'node_id') and item.node_id == 'root'), None)
            
            if root_node:
                ws.view.centerOn(root_node)
            else:
                ws.view.centerOn(0, 0)

    def on_bg_double_clicked(self, pos):
        """Crée un nœud au double-clic sur le fond de la scène."""
        ws = self.app.current_workspace()
        if not ws: return
        
        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        x, y = pos.x(), pos.y()
        if getattr(ws.scene, 'snap_to_grid', False):
            x = round(x / 20) * 20
            y = round(y / 20) * 20

        if not nodes:
            node = NodeItem('root', "Nouvelle idée centrale", x, y, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        else:
            unique_id = f"node_{int(time.time() * 1000)}"
            node = NodeItem(unique_id, "Nouvelle idée", x, y, bg='#FFF3E0', border='#FFB74D', font_color='#333333')
            
        if hasattr(self.app, 'editing_controller') and self.app.editing_controller:
            node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        ws.scene.addItem(node)
        
        if hasattr(self.app, 'save_state'):
            self.app.save_state()

    def handle_close_event(self, event):
        """Gère la fermeture globale de l'application (Interception et validation asynchrone)."""
        if not hasattr(self.app, 'tabs') or self.app.tabs is None:
            event.accept()
            return

        self.app.tabs.blockSignals(True)
        
        try:
            # 🚨 FIX CRITIQUE : Parcours inversé à rebours pour éviter les décalages d'index d'onglets
            for i in range(self.app.tabs.count() - 1, -1, -1):
                ws = self.app.tabs.widget(i)
                
                if ws and getattr(ws, 'is_dirty', False):
                    self.app.tabs.setCurrentIndex(i)
                    
                    file_path = getattr(ws, 'current_file_path', None)
                    name = file_path if file_path else f"Sans titre {i+1}"
                    
                    reply = QMessageBox.question(
                        self.app,
                        'Enregistrer les modifications',
                        f"Le document '{os.path.basename(name)}' a été modifié.\nVoulez-vous enregistrer les modifications ?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        # On force l'activation de l'espace de travail courant pour le service
                        if hasattr(self.app, 'project_service') and self.app.project_service:
                            # Tentative de sauvegarde
                            self.app.project_service.save_project()
                            
                            # Si l'espace est encore sale (l'utilisateur a fait Annuler dans la boîte de dialogue de fichier)
                            if getattr(ws, 'is_dirty', False):
                                self.app.tabs.blockSignals(False)
                                event.ignore()
                                return
                                
                    elif reply == QMessageBox.StandardButton.Cancel:
                        self.app.tabs.blockSignals(False)
                        event.ignore()
                        return
        finally:
            self.app.tabs.blockSignals(False)

        event.accept()