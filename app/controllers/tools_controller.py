# controllers/tools_controller.py
import json
import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class ToolsController:
    def __init__(self, app):
        self.app = app

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
       
    def apply_template(self, index):
        """Applique un fichier template JSON à la mind map courante."""
        if index == 0: return
        ws = self.app.current_workspace()
        if not ws: return
        
        filename = self.app.template_combo.itemData(index)
        self.app.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self.app, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            # Recherche du fichier dans le dossier 'templates' global
            template_path = ToolsController.resource_path(os.path.join("templates", filename))
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    state_str = data["content"] if "content" in data else json.dumps(data)
                    self.app.serializer.apply_state(state_str)
                    
                    ws.undo_stack.clear()
                    if hasattr(ws, 'redo_stack'):
                        ws.redo_stack.clear()
                        
                    ws.undo_stack.append(state_str)
                    ws.is_dirty = True
                    self.app.tabs_controller.update_title()
                    self.app.workspace_controller.center_on_graph()
                except Exception as e:
                    QMessageBox.critical(self.app, "Erreur", f"Erreur lors de la lecture du template :\n{str(e)}")
            else:
                QMessageBox.warning(self.app, "Erreur", f"Fichier template introuvable :\n{template_path}")

    def copy_selected(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            src = sel[0]
            self._clipboard_node = {
                "label": src.label,
                "shape": src.shape_type,
                "bg": src.bg_color.name(),
                "border": src.border_color.name(),
                "font_color": src.font_color.name(),
                "is_bold": src.is_bold,
                "status": src.status,
                "notes": getattr(src, 'notes', ''),
                "file_path": src.file_path,
                "url_link": src.url_link
            }

    def paste_node(self):
        ws = self.app.current_workspace()
        if not ws or not self._clipboard_node: return
        
        data = self._clipboard_node
        new_id = f"node_paste_{len(ws.scene.items())}"
        
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
        
        new_node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
        
        ws.scene.addItem(new_node)
        self.app.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)

    def auto_center_clicked(self):
        """Méthode appelée lors du clic sur le bouton Auto Center."""
        ws = self.app.current_workspace()
        if ws:
            # 1. On cherche d'abord le nœud racine ('root') dans la scène
            all_items = ws.scene.items()
            root_node = next((item for item in all_items if hasattr(item, 'node_id') and item.node_id == 'root'), None)
            
            if root_node:
                # Si le nœud root existe, on demande à la vue (QGraphicsView) de se centrer pile dessus
                ws.view.centerOn(root_node)
            else:
                # Repli de sécurité : si pas de root, on cadre sur toute la scène
                ws.view.centerOn(0, 0)

    def on_bg_double_clicked(self, pos):
        # On récupère le workspace via self.app
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
            # Génération d'un ID unique basé sur le temps en millisecondes
            import time
            unique_id = f"node_{int(time.time() * 1000)}"
            node = NodeItem(unique_id, "Nouvelle idée", x, y, bg='#FFF3E0', border='#FFB74D', font_color='#333333')
            
        if hasattr(self.app, 'editing_controller'):
            node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        ws.scene.addItem(node)
        
        # Sauvegarde du nouvel état pour le Ctrl+Z via l'application principale
        if hasattr(self.app, 'save_state'):
            self.app.save_state()

    def handle_close_event(self, event):
        """Gère la fermeture de l'application et force la sauvegarde des onglets non enregistrés."""
        
        # On bloque temporairement les signaux pour éviter les crashs de rafraîchissement (RuntimeError)
        self.app.tabs.blockSignals(True)
        
        try:
            # On boucle sur tous les onglets de l'application via self.app
            for i in range(self.app.tabs.count()):
                ws = self.app.tabs.widget(i)
                
                # Si l'onglet a été modifié (is_dirty)
                if hasattr(ws, 'is_dirty') and ws.is_dirty:
                    # On active l'onglet visuellement
                    self.app.tabs.setCurrentIndex(i)
                    
                    name = ws.current_file_path if ws.current_file_path else f"Sans titre {i+1}"
                    reply = QMessageBox.question(
                        self.app, # Le parent de la boîte de dialogue devient l'application
                        'Enregistrer les modifications',
                        f"Le document '{os.path.basename(name)}' a été modifié.\nVoulez-vous enregistrer les modifications ?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        # Appel du service de sauvegarde sur l'application
                        saved = self.app.project_service.save_project() 
                        
                        # Si la sauvegarde a été annulée par l'utilisateur, on intercepte et stoppe tout
                        if not saved:
                            self.app.tabs.blockSignals(False)
                            event.ignore()
                            return
                            
                    elif reply == QMessageBox.StandardButton.Cancel:
                        # L'utilisateur a cliqué sur Annuler : on stoppe complètement la fermeture
                        self.app.tabs.blockSignals(False)
                        event.ignore()
                        return
        finally:
            # Sécurité : On débloque toujours les signaux si l'application ne s'est finalement pas fermée
            self.app.tabs.blockSignals(False)

        # Si tout est validé/sauvegardé, on autorise la fermeture de la fenêtre
        event.accept()