import time
from graphics.items import BRANCH_PALETTES, NodeItem, EdgeItem

class GraphController:
    def __init__(self, app):
        self.app = app

    def _generate_unique_id(self, prefix="item"):
        """Génère un identifiant unique basé sur le temps pour éviter les collisions d'ID."""
        return f"{prefix}_{int(time.time() * 1000)}"

    def _apply_current_routing_mode(self, edge: EdgeItem) -> None:
        """Sécurité pour synchroniser le style de l'arête avec l'état actuel de la Toolbar."""
        if hasattr(self.app, 'btn_toggle_routing') and self.app.btn_toggle_routing:
            # Si ton EdgeItem utilise un attribut de routage (ex: 'is_curved' ou 'routing_type')
            # Ajuste le nom de l'attribut ci-dessous selon ton implémentation dans EdgeItem
            is_curved_mode = self.app.btn_toggle_routing.isChecked()
            if hasattr(edge, 'is_curved'):
                edge.is_curved = is_curved_mode
            elif hasattr(edge, 'set_curved'):
                edge.set_curved(is_curved_mode)

    def add_child_node(self, parent_node):
        """Ajoute un nœud enfant lié au nœud parent fourni et lance l'édition immédiate."""
        ws = self.app.current_workspace()
        if not ws or not parent_node: return
        
        new_id = self._generate_unique_id("node")
        t_x, t_y = self.calculate_smart_position(parent_node)
        
        # Gestion de l'aimantation à la grille
        if getattr(ws.scene, 'snap_to_grid', False):
            t_x = round(t_x / 20) * 20
            t_y = round(t_y / 20) * 20

        # Couleurs par défaut basées sur le parent
        bg = parent_node.bg_color.name() if hasattr(parent_node, 'bg_color') else '#FFFFFF'
        border = parent_node.border_color.name() if hasattr(parent_node, 'border_color') else '#000000'
        text_col = parent_node.font_color.name() if hasattr(parent_node, 'font_color') else '#000000'
        edge_col = '#A0AEC0'
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        
        # Attribution d'une palette de couleur distincte par branche si on part du nœud central
        if getattr(parent_node, 'node_id', None) == 'root':
            if BRANCH_PALETTES:
                pal = BRANCH_PALETTES[len(child_edges) % len(BRANCH_PALETTES)]
                bg, border, text_col, edge_col = pal['bg'], pal['border'], pal['text'], pal['edge']
        else:
            # Sinon, hérite de la couleur du lien parent
            p_edge = next((e for e in parent_node.edges if e.dest_node == parent_node), None)
            if p_edge and hasattr(p_edge, 'color'): 
                edge_col = p_edge.color.name()

        new_node = NodeItem(new_id, "Nouvelle sous-idée", t_x, t_y, shape='box', bg=bg, border=border, font_color=text_col)
        
        # Sécurité de liaison des signaux
        if hasattr(self.app, 'editing_controller'):
            new_node.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        edge_id = self._generate_unique_id("edge")
        edge = EdgeItem(edge_id, parent_node, new_node, "", color=edge_col)
        
        # 🟢 CORRECTION : On force l'état visuel du lien dès sa création
        self._apply_current_routing_mode(edge)
        
        if hasattr(self.app, 'editing_controller'):
            edge.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
        
        # Ajout et mise à jour de la scène
        ws.scene.addItem(new_node)
        ws.scene.addItem(edge)

        if hasattr(edge, 'update_position'):
            edge.update_position()
        
        # Enregistrement de l'arborescence interne dans les NodeItems
        if hasattr(parent_node, 'edges'): parent_node.edges.append(edge)
        if hasattr(new_node, 'edges'): new_node.edges.append(edge)
        
        self.app.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)
        
        if hasattr(self.app, 'editing_controller'):
            self.app.editing_controller.start_inline_editing(new_node)

    def calculate_smart_position(self, parent_node):
        """Calcule un emplacement libre à droite du nœud parent sans chevauchement."""
        ws = self.app.current_workspace()
        if not ws or not parent_node:
            return 150, 0
            
        parent_w = parent_node.rect.width() if hasattr(parent_node, 'rect') else 100
        parent_right_edge = parent_node.pos().x() + (parent_w / 2)
        target_x = parent_right_edge + 150
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node] if hasattr(parent_node, 'edges') else []
        if child_edges:
            lowest_y = parent_node.pos().y()
            for e in child_edges:
                if hasattr(e, 'dest_node') and e.dest_node.pos().y() > lowest_y: 
                    lowest_y = e.dest_node.pos().y()
            target_y = lowest_y + 85
        else:
            target_y = parent_node.pos().y()

        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        if len(all_nodes) <= 1:
            return target_x, target_y

        overlap = True
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
        """Supprime de manière sécurisée les éléments sélectionnés de la scène."""
        if hasattr(self.app, 'editing_controller') and getattr(self.app.editing_controller, 'editor', None) is not None: 
            return
            
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if not sel: return
        
        changed = False
        for item in sel:
            if isinstance(item, NodeItem) and getattr(item, 'node_id', None) == 'root':
                continue
                
            if isinstance(item, NodeItem):
                if getattr(item, 'file_path', None) and hasattr(self.app, 'attachment_controller'):
                    self.app.attachment_controller.remove_file_from_attachments(item.file_path)
                
                for edge in list(getattr(item, 'edges', [])):
                    if hasattr(edge, 'source_node') and edge in getattr(edge.source_node, 'edges', []): 
                        edge.source_node.edges.remove(edge)
                    if hasattr(edge, 'dest_node') and edge in getattr(edge.dest_node, 'edges', []): 
                        edge.dest_node.edges.remove(edge)
                    if edge.scene() == ws.scene: 
                        ws.scene.removeItem(edge)
                        
                if item.scene() == ws.scene: 
                    ws.scene.removeItem(item)
                changed = True
                
            elif isinstance(item, EdgeItem):
                if hasattr(item, 'source_node') and item in getattr(item.source_node, 'edges', []): 
                    item.source_node.edges.remove(item)
                if hasattr(item, 'dest_node') and item in getattr(item.dest_node, 'edges', []): 
                    item.dest_node.edges.remove(item)
                if item.scene() == ws.scene: 
                    ws.scene.removeItem(item)
                changed = True
                    
        if changed:
            self.app.save_state()

    def connect_selected_nodes(self):
        """Relie deux nœuds distincts sélectionnés ensemble par un lien personnalisé."""
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        
        if len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            node1, node2 = sel[0], sel[1]
            
            edges1 = getattr(node1, 'edges', [])
            already_linked = any(
                (getattr(e, 'source_node', None) == node1 and getattr(e, 'dest_node', None) == node2) or 
                (getattr(e, 'source_node', None) == node2 and getattr(e, 'dest_node', None) == node1) 
                for e in edges1
            )
            
            if not already_linked:
                link_color = getattr(node1, 'border_color', None)
                edge_id = self._generate_unique_id("edge")
                edge = EdgeItem(edge_id, node1, node2, "", color=link_color)
                
                # 🟢 CORRECTION : Appliqué également lors d'une connexion manuelle entre 2 nœuds
                self._apply_current_routing_mode(edge)
                
                if hasattr(self.app, 'editing_controller'):
                    edge.signals.itemDoubleClicked.connect(self.app.editing_controller.start_inline_editing)
                
                ws.scene.addItem(edge)

                if hasattr(edge, 'update_position'):
                    edge.update_position()
                
                if hasattr(node1, 'edges'): node1.edges.append(edge)
                if hasattr(node2, 'edges'): node2.edges.append(edge)
                
                ws.scene.clearSelection()
                edge.setSelected(True)
                self.app.save_state()

    def filter_nodes(self, search_text):
        """Filtre visuellement les nœuds de la Mind Map en modifiant leur opacité."""
        ws = self.app.current_workspace()
        if not ws:
            return
        
        # On passe la recherche en minuscules pour ne pas être sensible à la casse
        search_text = search_text.lower().strip()
        
        # On importe NodeItem ici pour éviter les imports circulaires si nécessaire
        from graphics.items import NodeItem
        
        for item in ws.scene.items():
            if isinstance(item, NodeItem):
                # Si la recherche est vide ou si le texte du nœud contient le mot recherché
                if not search_text or search_text in item.label.lower():
                    item.setOpacity(1.0)  # Totalement opaque / visible
                else:
                    item.setOpacity(0.2)  # Semi-transparent / estompé