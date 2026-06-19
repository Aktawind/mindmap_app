import json
from graphics.items import NodeItem, EdgeItem

class MindMapSerializer:
    def __init__(self, app):
        self.app = app

    def get_state(self):
        ws = self.app.current_workspace()
        if not ws: return {}
        
        all_items = ws.scene.items()
        nodes = [i for i in all_items if isinstance(i, NodeItem)]
        edges = [i for i in all_items if isinstance(i, EdgeItem)]
        
        root = next((n for n in nodes if n.node_id == 'root'), None) or (nodes[0] if nodes else None)
        if not root: return {}

        natural_edges = set()
        serialized_node_ids = set()

        def serialize_node(node):
            serialized_node_ids.add(node.node_id)
            data = {
                "id": node.node_id,
                "label": node.label,
                "x": node.pos().x(),
                "y": node.pos().y(),
                "shape": node.shape_type,
                "bg": node.bg_color.name(),
                "border": node.border_color.name(),
                "font_color": node.font_color.name(),
                "border_width": node.border_width,
                "is_bold": node.is_bold,
                "status": node.status,
                "file_path": node.file_path,
                "url_link": node.url_link,
                "children": []
            }
            for edge in node.edges:
                if edge.source_node == node:
                    natural_edges.add(edge)
                    child_data = serialize_node(edge.dest_node)
                    if edge.label: child_data["edge_label"] = edge.label
                    child_data["edge_arrow_dir"] = edge.arrow_dir
                    data["children"].append(child_data)
            return data

        tree_data = serialize_node(root)
        tree_data["global_line_routing"] = ws.scene.line_routing_mode
        tree_data["snap_to_grid"] = getattr(ws.scene, 'snap_to_grid', False)

        orphan_nodes_data = []
        for node in nodes:
            if node.node_id not in serialized_node_ids:
                orphan_nodes_data.append({
                    "id": node.node_id,
                    "label": node.label,
                    "x": node.pos().x(),
                    "y": node.pos().y(),
                    "shape": node.shape_type,
                    "bg": node.bg_color.name(),
                    "border": node.border_color.name(),
                    "font_color": node.font_color.name(),
                    "border_width": node.border_width,
                    "is_bold": node.is_bold,
                    "status": node.status,
                    "file_path": node.file_path,
                    "url_link": node.url_link
                })
        tree_data["orphan_nodes"] = orphan_nodes_data

        cross_links_data = []
        for edge in edges:
            if edge not in natural_edges:
                cross_links_data.append({
                    "from": edge.source_node.node_id,
                    "to": edge.dest_node.node_id,
                    "label": edge.label,
                    "color": edge.color.name(),
                    "arrow_dir": edge.arrow_dir
                })

        tree_data["cross_links"] = cross_links_data
        return tree_data
    
    def apply_state(self, state_data):
        # CORRECTION : On accède au workspace via self.app
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

        ws.scene.line_routing_mode = root_data.get("global_line_routing", "curved")
        ws.scene.snap_to_grid = root_data.get("snap_to_grid", False)
        
        # CORRECTION : Utilisation de self.app pour l'UI
        self.app.sync_workspace_ui({
            "snap_to_grid": ws.scene.snap_to_grid,
            "line_routing_mode": ws.scene.line_routing_mode
        })
        
        node_counter = [0]
        edge_counter = [0]
        created_nodes = {}

        def deserialize_node(data, parent_node=None):
            if not data: return None
            node_counter[0] += 1
            node_id = data.get("id") or ('root' if parent_node is None else f"node_{node_counter[0]}")
            
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
                is_bold=data.get("is_bold", False), status=status
            )
            node.border_width = data.get("border_width", 1)
            # CORRECTION : start_inline_editing appartient à self.app
            node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
            ws.scene.addItem(node)
            created_nodes[node_id] = node

            if parent_node:
                edge_counter[0] += 1
                edge_color = border if parent_node.node_id != 'root' else '#A0AEC0'
                edge = EdgeItem(f"edge_{edge_counter[0]}", parent_node, node, data.get("edge_label", ""), color=edge_color, arrow_dir=data.get("edge_arrow_dir", "none"))
                # CORRECTION : idem ici
                edge.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
                ws.scene.addItem(edge)

            for child_data in data.get("children", []):
                deserialize_node(child_data, node)
            return node

        deserialize_node(root_data)

        for orphan in root_data.get("orphan_nodes", []):
            node_id = orphan.get("id")
            node = NodeItem(
                node_id, orphan.get("label", ""), orphan.get("x", 0.0), orphan.get("y", 0.0),
                shape=orphan.get("shape", "box"), bg=orphan.get("bg", '#60A5FA'),
                border=orphan.get("border", '#3B82F6'), font_color=orphan.get("font_color", '#ffffff'),
                file_path=orphan.get("file_path"), url_link=orphan.get("url_link"),
                is_bold=orphan.get("is_bold", False), status=orphan.get("status", "none")
            )
            node.border_width = orphan.get("border_width", 1)
            node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
            ws.scene.addItem(node)
            created_nodes[node_id] = node

        for cl in root_data.get("cross_links", []):
            source = created_nodes.get(cl["from"])
            dest = created_nodes.get(cl["to"])
            if source and dest:
                edge_counter[0] += 1
                edge = EdgeItem(f"edge_{edge_counter[0]}", source, dest, cl.get("label", ""), color=cl.get("color", "#A0AEC0"), arrow_dir=cl.get("arrow_dir", "none"))
                edge.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
                ws.scene.addItem(edge)

        ws.is_applying_state = False
        self.app.on_selection_changed()