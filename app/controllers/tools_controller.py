import copy
import json
import os
import sys
import time
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QWidget
from graphics.items import NodeItem, EdgeItem

class ToolsController:
    def __init__(self, app):
        self.app = app
        self._clipboard_node = None  # Rétrocompatibilité (non utilisé, voir _clipboard_nodes/_clipboard_edges)
        self._clipboard_nodes = []
        self._clipboard_edges = []

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
        """Demande confirmation et génère le template dans un nouvel onglet dédié."""
        if index == 0: return
        
        if not hasattr(self.app, 'template_combo') or self.app.template_combo is None: return
        
        # Récupération des métadonnées du template sélectionné
        template_name = self.app.template_combo.itemText(index)
        filename = self.app.template_combo.itemData(index)
        
        # Remet immédiatement l'index à 0 pour la Toolbar
        self.app.template_combo.setCurrentIndex(0)
        
        # 🟢 NOUVEAU COMPORTEMENT : Demande de création d'un nouvel onglet
        msg = f"Voulez-vous ouvrir le template '{template_name}' dans un nouvel onglet ?"
        reply = QMessageBox.question(
            self.app, 
            "Ouvrir un Template", 
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            template_path = ToolsController.resource_path(os.path.join("templates", filename))
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    state_str = data["content"] if "content" in data else json.dumps(data)
                    
                    # 1. Génération du nouvel onglet via le ProjectService
                    if hasattr(self.app, 'project_service') and self.app.project_service:
                        self.app.project_service.new_project()
                    
                    # 2. Récupération du workspace de ce nouvel onglet créé
                    ws = self.app.current_workspace()
                    if not ws: return
                    
                    # Renomme l'onglet temporairement avec le nom du template
                    if hasattr(self.app, 'tabs') and self.app.tabs:
                        current_idx = self.app.tabs.currentIndex()
                        self.app.tabs.setTabText(current_idx, f"[{template_name}]")
                    
                    # 3. Application du template sur le nouvel onglet propre
                    if hasattr(self.app, 'serializer') and self.app.serializer:
                        # Nettoie d'abord le nœud par défaut généré par new_project
                        ws.scene.clear() 
                        self.app.serializer.apply_state(state_str)
                    
                    # Réinitialisation de l'historique sur le nouvel onglet
                    if hasattr(ws, 'undo_stack'): ws.undo_stack.clear()
                    if hasattr(ws, 'redo_stack'): ws.redo_stack.clear()
                    
                    # Conversion de state_str en dict si ton undo_stack attend un dictionnaire 
                    # (vu dans ton ProjectService précédent)
                    try:
                        state_dict = json.loads(state_str) if isinstance(state_str, str) else state_str
                        ws.undo_stack.append(state_dict)
                    except Exception:
                        ws.undo_stack.append(state_str)
                        
                    ws.is_dirty = True
                    
                    if hasattr(self.app, 'tabs_controller'):
                        self.app.tabs_controller.update_title()
                    if hasattr(self.app, 'workspace_controller'):
                        self.app.workspace_controller.center_on_graph()
                        
                except Exception as e:
                    QMessageBox.critical(self.app, "Erreur", f"Erreur lors du chargement du template :\n{str(e)}")
            else:
                QMessageBox.warning(self.app, "Erreur", f"Fichier template introuvable :\n{template_path}")

    @staticmethod
    def _snapshot_node(node):
        """Capture toutes les propriétés reconstructibles d'un nœud, pour le presse-papier interne."""
        return {
            "label": getattr(node, 'label', ''),
            "shape": getattr(node, 'shape_type', 'box'),
            "bg": node.bg_color.name() if hasattr(node, 'bg_color') else '#60A5FA',
            "border": node.border_color.name() if hasattr(node, 'border_color') else '#3B82F6',
            "font_color": node.font_color.name() if hasattr(node, 'font_color') else '#ffffff',
            "is_bold": getattr(node, 'is_bold', False),
            "is_italic": getattr(node, 'is_italic', False),
            "is_strikethrough": getattr(node, 'is_strikethrough', False),
            "status": getattr(node, 'status', 'none'),
            "priority": getattr(node, 'priority', 'none'),
            "date": getattr(node, 'date', None),
            "is_compact": getattr(node, 'is_compact', False),
            "notes": getattr(node, 'notes', ''),
            "node_format": getattr(node, 'node_format', 'default'),
            "attachments": copy.deepcopy(getattr(node, 'attachments', [])),
            "image_path": getattr(node, 'image_path', None),
            "image_height": getattr(node, 'image_height', 150),
        }

    def copy_selected(self):
        """Copie tous les nœuds sélectionnés (et les branches qui les relient entre eux) dans le
        presse-papier interne, partagé entre tous les onglets."""
        ws = self.app.current_workspace()
        if not ws: return

        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if not nodes: return

        selected_ids = {n.node_id for n in nodes}

        self._clipboard_nodes = []
        for node in nodes:
            snapshot = self._snapshot_node(node)
            snapshot["_source_id"] = node.node_id
            snapshot["_x"] = node.pos().x()
            snapshot["_y"] = node.pos().y()
            self._clipboard_nodes.append(snapshot)

        # Capture des branches internes au groupe copié (les deux extrémités doivent être sélectionnées)
        seen_edges = set()
        self._clipboard_edges = []
        for node in nodes:
            for edge in getattr(node, 'edges', []):
                source = getattr(edge, 'source_node', None)
                dest = getattr(edge, 'dest_node', None)
                if not source or not dest or id(edge) in seen_edges:
                    continue
                if source.node_id in selected_ids and dest.node_id in selected_ids:
                    seen_edges.add(id(edge))
                    self._clipboard_edges.append({
                        "from": source.node_id,
                        "to": dest.node_id,
                        "label": getattr(edge, 'label', ''),
                        "color": edge.color.name() if hasattr(edge, 'color') else '#A0AEC0',
                        "arrow_dir": getattr(edge, 'arrow_dir', 'none'),
                    })

    def paste_node(self):
        """Colle les nœuds du presse-papier (et leurs branches internes) autour de l'emplacement
        central de la vue courante, en conservant leurs positions relatives. Fonctionne d'un
        onglet à l'autre puisque le presse-papier est partagé au niveau de l'application."""
        ws = self.app.current_workspace()
        if not ws or not self._clipboard_nodes: return

        center = ws.view.mapToScene(ws.view.viewport().rect().center())

        # Décalage nécessaire pour amener le centre du groupe copié sur le centre de la vue
        avg_x = sum(n["_x"] for n in self._clipboard_nodes) / len(self._clipboard_nodes)
        avg_y = sum(n["_y"] for n in self._clipboard_nodes) / len(self._clipboard_nodes)
        offset_x, offset_y = center.x() - avg_x, center.y() - avg_y

        id_map = {}
        new_nodes = []
        base_timestamp = int(time.time() * 1000)

        for i, data in enumerate(self._clipboard_nodes):
            new_id = f"node_paste_{base_timestamp}_{i}"
            id_map[data["_source_id"]] = new_id

            x, y = data["_x"] + offset_x, data["_y"] + offset_y
            if getattr(ws.scene, 'snap_to_grid', False):
                x = round(x / 20) * 20
                y = round(y / 20) * 20

            new_node = NodeItem(
                new_id, data["label"], x, y,
                shape=data["shape"], bg=data["bg"], border=data["border"], font_color=data["font_color"],
                is_bold=data["is_bold"], is_italic=data.get("is_italic", False),
                is_strikethrough=data.get("is_strikethrough", False), status=data["status"],
                priority=data.get("priority", "none"), is_compact=data.get("is_compact", False),
                image_path=data.get("image_path"), image_height=data.get("image_height", 150),
                node_format=data.get("node_format", "default"),
            )
            if hasattr(new_node, 'notes'): new_node.notes = data["notes"]
            new_node.date = data.get("date")
            new_node.attachments = copy.deepcopy(data.get("attachments", []))
            new_node.recalculate_size()

            if hasattr(self.app, 'editing_controller') and self.app.editing_controller:
                new_node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
            elif hasattr(self.app, 'start_inline_editing'):
                new_node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)

            ws.scene.addItem(new_node)
            new_nodes.append(new_node)

        # Recrée les branches internes au groupe collé, en pointant vers les nouveaux identifiants
        for i, edge_data in enumerate(self._clipboard_edges):
            source = next((n for n in new_nodes if n.node_id == id_map.get(edge_data["from"])), None)
            dest = next((n for n in new_nodes if n.node_id == id_map.get(edge_data["to"])), None)
            if not source or not dest:
                continue

            edge_id = f"edge_paste_{base_timestamp}_{i}"
            edge = EdgeItem(edge_id, source, dest, edge_data.get("label", ""),
                             color=edge_data.get("color", "#A0AEC0"), arrow_dir=edge_data.get("arrow_dir", "none"))

            if hasattr(self.app, 'editing_controller') and self.app.editing_controller:
                edge.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)

            ws.scene.addItem(edge)
            if hasattr(edge, 'update_position'): edge.update_position()
            source.edges.append(edge)
            dest.edges.append(edge)

        if hasattr(self.app, 'save_state'):
            self.app.save_state()

        ws.scene.clearSelection()
        for node in new_nodes:
            node.setSelected(True)

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

    def fit_to_view_clicked(self):
        """Ajuste le zoom et la position de la vue pour englober l'intégralité de la carte."""
        ws = self.app.current_workspace()
        if not ws: return

        rect = ws.scene.itemsBoundingRect()
        if rect.isEmpty(): return

        margin = 60
        rect = rect.adjusted(-margin, -margin, margin, margin)
        ws.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

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