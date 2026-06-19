# controllers/graph_controller.py
import math
from PyQt6.QtCore import QPointF
from graphics.items import BRANCH_PALETTES, NodeItem, EdgeItem

class GraphController:
    def __init__(self, app):
        self.app = app

    def add_child_node(self, parent_node):
        ws = self.app.current_workspace()
        new_id = f"node_{len(ws.scene.items())}"
        
        t_x, t_y = self.calculate_smart_position(parent_node)
        if getattr(ws.scene, 'snap_to_grid', False):
            t_x = round(t_x / 20) * 20
            t_y = round(t_y / 20) * 20

        bg, border, text_col, edge_col = parent_node.bg_color.name(), parent_node.border_color.name(), parent_node.font_color.name(), '#A0AEC0'
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        
        if parent_node.node_id == 'root':
            pal = BRANCH_PALETTES[len(child_edges) % len(BRANCH_PALETTES)]
            bg, border, text_col, edge_col = pal['bg'], pal['border'], pal['text'], pal['edge']
        else:
            p_edge = next((e for e in parent_node.edges if e.dest_node == parent_node), None)
            if p_edge: edge_col = p_edge.color.name()

        new_node = NodeItem(new_id, "Nouvelle sous-idée", t_x, t_y, shape='box', bg=bg, border=border, font_color=text_col)
        new_node.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
        
        edge = EdgeItem(f"edge_{len(ws.scene.items())}", parent_node, new_node, "", color=edge_col)
        edge.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
        
        ws.scene.addItem(new_node)
        ws.scene.addItem(edge)
        self.app.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)
        self.app.start_inline_editing(new_node)

    def calculate_smart_position(self, parent_node):
        ws = self.app.current_workspace()
        if not ws or not parent_node:
            return 150, 0
            
        parent_right_edge = parent_node.pos().x() + (parent_node.rect.width() / 2)
        target_x = parent_right_edge + 150
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        if child_edges:
            lowest_y = parent_node.pos().y()
            for e in child_edges:
                if e.dest_node.pos().y() > lowest_y: 
                    lowest_y = e.dest_node.pos().y()
            target_y = lowest_y + 85
        else:
            target_y = parent_node.pos().y()

        overlap = True
        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        if len(all_nodes) <= 1:
            return target_x, target_y

        iterations = 0
        while overlap and iterations < 100:
            overlap = False
            iterations += 1
            for n in all_nodes:
                if n == parent_node: 
                    continue
                if abs(n.pos().x() - target_x) < 180 and abs(n.pos().y() - target_y) < 65:
                    target_y += 85
                    overlap = True
                    break
        return target_x, target_y

    def delete_selected(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if not sel: return
        
        for item in sel:
            if isinstance(item, NodeItem):
                if item.file_path:
                    self.remove_file_from_attachments(ws, item.file_path)
                for edge in list(item.edges):
                    if edge in edge.source_node.edges: edge.source_node.edges.remove(edge)
                    if edge in edge.dest_node.edges: edge.dest_node.edges.remove(edge)
                    if edge.scene() == ws.scene: ws.scene.removeItem(edge)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
            elif isinstance(item, EdgeItem):
                if item in item.source_node.edges: item.source_node.edges.remove(item)
                if item in item.dest_node.edges: item.dest_node.edges.remove(item)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
                    
        self.app.save_state()

    def connect_selected_nodes(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            node1, node2 = sel[0], sel[1]
            already_linked = any(
                (e.source_node == node1 and e.dest_node == node2) or 
                (e.source_node == node2 and e.dest_node == node1) 
                for e in node1.edges
            )
            if not already_linked:
                link_color = node1.border_color
                edge = EdgeItem(f"edge_{len(ws.scene.items())}", node1, node2, "", color=link_color)
                edge.signals.itemDoubleClicked.connect(self.app.start_inline_editing)
                ws.scene.addItem(edge)
                ws.scene.clearSelection()
                edge.setSelected(True)
                self.app.save_state()