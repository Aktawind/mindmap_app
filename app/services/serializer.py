import json
import os
from platform import node
from graphics.items import NodeItem, EdgeItem
from ui.selection_manager import on_selection_changed

class MindMapSerializer:
    def __init__(self, app):
        self.app = app

    def get_state(self):
        """Sérialise l'état complet du workspace actif dans un dictionnaire Python."""
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None: 
            return {}
        
        all_items = ws.scene.items()
        nodes = [i for i in all_items if isinstance(i, NodeItem)]
        edges = [i for i in all_items if isinstance(i, EdgeItem)]
        
        root = next((n for n in nodes if n.node_id == 'root'), None) or (nodes[0] if nodes else None)
        if not root: 
            return {}

        natural_edges = set()
        serialized_node_ids = set()

        def serialize_node(node):
            if not node: return None
            
            # SÉCURITÉ ANTI-BOUCLE INFINIE À LA SAUVEGARDE
            if node.node_id in serialized_node_ids:
                return None
                
            serialized_node_ids.add(node.node_id)
            
            data = {
                "id": node.node_id,
                "label": getattr(node, 'label', ''),
                "x": node.pos().x(),
                "y": node.pos().y(),
                "shape": getattr(node, 'shape_type', 'box'),
                "bg": node.bg_color.name() if hasattr(node, 'bg_color') else '#60A5FA',
                "border": node.border_color.name() if hasattr(node, 'border_color') else '#3B82F6',
                "font_color": node.font_color.name() if hasattr(node, 'font_color') else '#ffffff',
                "border_width": getattr(node, 'border_width', 1),
                "is_bold": getattr(node, 'is_bold', False),
                "is_italic": getattr(node, 'is_italic', False),       
                "is_strikethrough": getattr(node, 'is_strikethrough', False), 
                "status": getattr(node, 'status', 'none'),
                "attachments": getattr(node, 'attachments', []),
                "url_link": getattr(node, 'url_link', None),
                "date": getattr(node, 'date', None),
                "priority": getattr(node, 'priority', "none"),
                "is_compact": getattr(node, 'is_compact', False),
                "children": []
            }
            
            for edge in getattr(node, 'edges', []):
                if getattr(edge, 'source_node', None) == node and hasattr(edge, 'dest_node') and edge.dest_node:
                    
                    # SÉCURITÉ SUPPLÉMENTAIRE
                    if edge.dest_node.node_id in serialized_node_ids:
                        continue
                        
                    natural_edges.add(edge)
                    child_data = serialize_node(edge.dest_node)
                    if child_data:
                        child_data["edge_label"] = getattr(edge, 'label', '')
                        child_data["edge_arrow_dir"] = getattr(edge, 'arrow_dir', 'none')
                        data["children"].append(child_data)
            return data

        # Structuration propre du JSON global
        state = {
            "global_line_routing": getattr(ws.scene, 'line_routing_mode', 'curved'),
            "snap_to_grid": getattr(ws.scene, 'snap_to_grid', False),
            "root": serialize_node(root),
            "orphan_nodes": [],
            "cross_links": []
        }

        # Collecte des nœuds orphelins
        for node in nodes:
            if node.node_id not in serialized_node_ids:
                state["orphan_nodes"].append({
                    "id": node.node_id,
                    "label": getattr(node, 'label', ''),
                    "x": node.pos().x(),
                    "y": node.pos().y(),
                    "shape": getattr(node, 'shape_type', 'box'),
                    "bg": node.bg_color.name() if hasattr(node, 'bg_color') else '#60A5FA',
                    "border": node.border_color.name() if hasattr(node, 'border_color') else '#3B82F6',
                    "font_color": node.font_color.name() if hasattr(node, 'font_color') else '#ffffff',
                    "border_width": getattr(node, 'border_width', 1),
                    "is_bold": getattr(node, 'is_bold', False),
                    "is_italic": getattr(node, 'is_italic', False),
                    "is_strikethrough": getattr(node, 'is_strikethrough', False),
                    "status": getattr(node, 'status', 'none'),
                    "attachments": getattr(node, 'attachments', []),
                    "url_link": getattr(node, 'url_link', None),
                    "date": getattr(node, 'date', None),
                    "priority": getattr(node, 'priority', "none"),
                    "is_compact": getattr(node, 'is_compact', False)
                })

        # Collecte des liens transversaux (Cross Links)
        for edge in edges:
            if edge not in natural_edges and getattr(edge, 'source_node', None) and getattr(edge, 'dest_node', None):
                state["cross_links"].append({
                    "from": edge.source_node.node_id,
                    "to": edge.dest_node.node_id,
                    "label": getattr(edge, 'label', ''),
                    "color": edge.color.name() if hasattr(edge, 'color') else '#A0AEC0',
                    "arrow_dir": getattr(edge, 'arrow_dir', 'none')
                })

        return state
    
    def apply_state(self, state_data):
        """Applique l'état sauvegardé à la scène courante."""
        if isinstance(state_data, str):
            try:
                state_data = json.loads(state_data)
            except Exception as e:
                print(f"Erreur lors du décodage du state_str : {e}")
                return

        root_data = state_data.get("root", state_data) if isinstance(state_data, dict) else {}
        
        if isinstance(root_data, str):
            try:
                root_data = json.loads(root_data)
            except:
                root_data = {}

        ws = self.app.current_workspace()
        if not ws or state_data is None: return
        
        if isinstance(state_data, str):
            if not state_data.strip(): return
            try:
                root_data = json.loads(state_data)
            except Exception:
                return
        else:
            root_data = state_data

        ws.is_applying_state = True
        ws.scene.clear()

        # Restauration des configurations globales de la scène
        ws.scene.line_routing_mode = root_data.get("global_line_routing", "curved")
        ws.scene.snap_to_grid = root_data.get("snap_to_grid", False)
        
        # Synchronisation de l'interface graphique globale
        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.sync_workspace_ui({
                "snap_to_grid": ws.scene.snap_to_grid,
                "line_routing_mode": ws.scene.line_routing_mode
            })
        
        node_counter = [0]
        edge_counter = [0]
        created_nodes = {}

        def deserialize_node(data, parent_node=None):
            if not data: return None
            
            node_id = data.get("id") or ('root' if parent_node is None else f"node_{node_counter[0]}")
            
            # 🚨 SÉCURITÉ ANTI-DOUBLON
            if node_id in created_nodes:
                return created_nodes[node_id]
                
            node_counter[0] += 1
            x, y = data.get("x", 0.0), data.get("y", 0.0)
            bg = data.get("bg", '#60A5FA')
            border = data.get("border", '#3B82F6')
            font_color = data.get("font_color", '#ffffff')

            status = data.get("status", "none")
            raw_label = data.get("label", "")
            if status == "none" and raw_label.startswith("🚨 "):
                status = "urgent"

            clean_label = raw_label.replace("\n📄 Document joint", "").replace("\n🔗 Lien URL", "")

            node = NodeItem(
                node_id, clean_label, x, y,
                shape=data.get("shape", "box"), bg=bg, border=border, font_color=font_color,
                file_path=data.get("file_path"), url_link=data.get("url_link"), 
                is_bold=data.get("is_bold", False),  is_italic=data.get("is_italic", False), 
                is_strikethrough=data.get("is_strikethrough", False), status=status
            )
            node.border_width = data.get("border_width", 1)

            node.date = data.get("date", None)
            priority = data.get("priority")          
            node.priority = priority if priority == 'null' else "none"
            node.is_compact = data.get("is_compact", False)

            if "attachments" in data:
                node.attachments = data["attachments"]
            else:
                node.attachments = []
                old_path = data.get("file_path")
                if old_path:
                    node.attachments.append({
                        "name": os.path.basename(old_path),
                        "path": old_path,
                        "is_local_copy": True
                    })
            
            node.recalculate_size()
            
            if hasattr(self.app, 'editing_controller'):
                node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
                
            ws.scene.addItem(node)
            created_nodes[node_id] = node

            if parent_node:
                edge_counter[0] += 1
                edge_color = border if parent_node.node_id != 'root' else '#A0AEC0'
                edge = EdgeItem(f"edge_{edge_counter[0]}", parent_node, node, data.get("edge_label", ""), color=edge_color, arrow_dir=data.get("edge_arrow_dir", "none"))
                
                if hasattr(self.app, 'editing_controller'):
                    edge.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
                
                ws.scene.addItem(edge)
                
                if not hasattr(parent_node, 'edges'): parent_node.edges = []
                if not hasattr(node, 'edges'): node.edges = []
                parent_node.edges.append(edge)
                node.edges.append(edge)

            for child_data in data.get("children", []):
                deserialize_node(child_data, node)
            return node

        # 1. Chargement de l'arbre principal
        tree_root_data = root_data.get("root") if "root" in root_data else root_data
        deserialize_node(tree_root_data)

        # 2. Restauration des nœuds orphelins
        for orphan in root_data.get("orphan_nodes", []):
            node_id = orphan.get("id")
            
            if node_id in created_nodes:
                continue
                
            node = NodeItem(
                node_id, orphan.get("label", ""), orphan.get("x", 0.0), orphan.get("y", 0.0),
                shape=orphan.get("shape", "box"), bg=orphan.get("bg", '#60A5FA'),
                border=orphan.get("border", '#3B82F6'), font_color=orphan.get("font_color", '#ffffff'),
                file_path=orphan.get("file_path"), url_link=orphan.get("url_link"),
                is_bold=orphan.get("is_bold", False), is_italic=orphan.get("is_italic", False),
                is_strikethrough=orphan.get("is_strikethrough", False), status=orphan.get("status", "none")
            )
            node.border_width = orphan.get("border_width", 1)

            node.date = orphan.get("date", None)
            node.priority = orphan.get("priority", "none")
            node.is_compact = orphan.get("is_compact", False)

            if "attachments" in orphan:
                node.attachments = orphan["attachments"]
            else:
                node.attachments = []
                old_path = orphan.get("file_path")
                if old_path:
                    node.attachments.append({
                        "name": os.path.basename(old_path),
                        "path": old_path,
                        "is_local_copy": True
                    })
                    
            node.recalculate_size()
            
            if hasattr(self.app, 'editing_controller'):
                node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
                
            ws.scene.addItem(node)
            created_nodes[node_id] = node

        # 3. Restauration des liens transversaux (Cross Links)
        for cl in root_data.get("cross_links", []):
            source = created_nodes.get(cl["from"])
            dest = created_nodes.get(cl["to"])
            if source and dest:
                edge_counter[0] += 1
                edge = EdgeItem(f"edge_{edge_counter[0]}", source, dest, cl.get("label", ""), color=cl.get("color", "#A0AEC0"), arrow_dir=cl.get("arrow_dir", "none"))
                
                if hasattr(self.app, 'editing_controller'):
                    edge.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
                
                ws.scene.addItem(edge)
                
                if not hasattr(source, 'edges'): source.edges = []
                if not hasattr(dest, 'edges'): dest.edges = []
                source.edges.append(edge)
                dest.edges.append(edge)

        # Rafraîchissement géométrique forcé de toutes les arêtes
        for item in ws.scene.items():
            if isinstance(item, EdgeItem):
                if hasattr(item, 'update_position'): item.update_position()
                elif hasattr(item, 'update_path'): item.update_path()
                item.update()

        ws.is_applying_state = False
        on_selection_changed(self.app)

        # Force le bouton ou le widget de la toolbar à lire l'état qui vient d'être chargé
        if hasattr(self.app, 'routing_controller'):
            self.app.routing_controller.update_routing_button_ui()