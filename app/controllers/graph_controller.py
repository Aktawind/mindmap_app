import time
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QFont, QFontMetrics
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
            is_curved_mode = self.app.btn_toggle_routing.isChecked()
            if hasattr(edge, 'is_curved'):
                edge.is_curved = is_curved_mode
            elif hasattr(edge, 'set_curved'):
                edge.set_curved(is_curved_mode)

    def toggle_node_collapsed(self, node):
        """Plie/déplie les enfants hiérarchiques du nœud donné, et sauvegarde immédiatement
        pour que l'état plié survive à une fermeture/réouverture de la carte."""
        node.is_collapsed = not node.is_collapsed
        self.refresh_fold_visibility()
        ws = self.app.current_workspace()
        if ws:
            ws.is_dirty = True
        if hasattr(self.app, 'save_state'):
            self.app.save_state()

    def refresh_fold_visibility(self):
        """Cache ou affiche les nœuds/arêtes de la carte active selon l'état plié (is_collapsed)
        de leurs ancêtres hiérarchiques. Ne suit que les arêtes parent -> enfant : un lien
        transversal ("Relier les nœuds") ne fait jamais partie d'un pliage."""
        ws = self.app.current_workspace()
        if not ws:
            return

        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        edges = [i for i in ws.scene.items() if isinstance(i, EdgeItem)]
        root = next((n for n in nodes if n.node_id == 'root'), None)

        hidden_ids = set()
        if root:
            def walk(node, ancestor_collapsed):
                for child in node.hierarchy_children():
                    if ancestor_collapsed:
                        hidden_ids.add(child.node_id)
                    walk(child, ancestor_collapsed or getattr(child, 'is_collapsed', False))
            walk(root, getattr(root, 'is_collapsed', False))

        for n in nodes:
            n.setVisible(n.node_id not in hidden_ids)

        for e in edges:
            src_hidden = getattr(e.source_node, 'node_id', None) in hidden_ids
            dst_hidden = getattr(e.dest_node, 'node_id', None) in hidden_ids
            e.setVisible(not (src_hidden or dst_hidden))

    def auto_layout(self):
        """Réorganise automatiquement l'arborescence connectée à la racine en un agencement
        de type mind map classique : la racine reste au centre, et ses branches principales
        se répartissent de part et d'autre (gauche/droite, équilibrées par hauteur totale de
        sous-arbre), chaque branche s'étalant horizontalement vers l'extérieur par niveaux de
        profondeur. Les nœuds orphelins ou reliés uniquement via "Relier les nœuds" ne font
        pas partie de l'arbre naturel et ne sont donc pas déplacés."""
        ws = self.app.current_workspace()
        if not ws: return

        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        root = next((n for n in nodes if n.node_id == 'root'), None)
        if not root: return

        LEVEL_GAP = 50
        SIBLING_GAP = 12

        visited_ids = {root.node_id}
        tree_children = {}
        # Arête (avec son libellé éventuel) entre un nœud et chacun de ses enfants naturels,
        # pour pouvoir élargir l'espacement d'un niveau si une branche y porte du texte.
        child_edge = {}

        def get_children(node):
            children = []
            for edge in getattr(node, 'edges', []):
                if getattr(edge, 'source_node', None) == node:
                    child = getattr(edge, 'dest_node', None)
                    if child and child.node_id not in visited_ids:
                        visited_ids.add(child.node_id)
                        children.append(child)
                        child_edge[child.node_id] = edge
            return children

        _label_font = QFont('Segoe UI', 10)
        _label_fm = QFontMetrics(_label_font)

        def label_extra_gap(child):
            """Espace supplémentaire à réserver si la branche menant à ce nœud porte un
            libellé, pour que le texte ne soit pas écrasé entre les deux colonnes de nœuds."""
            edge = child_edge.get(child.node_id)
            label = getattr(edge, 'label', '') if edge else ''
            if not label:
                return 0
            widest_line = max((_label_fm.horizontalAdvance(line) for line in label.split('\n')), default=0)
            return widest_line + 40  # marge du cadre du libellé + respiration de part et d'autre

        def build_tree(node):
            children = get_children(node)
            tree_children[node.node_id] = children
            for child in children:
                build_tree(child)

        root_children = get_children(root)
        for child in root_children:
            build_tree(child)

        subtree_height = {}

        def compute_height(node):
            children = tree_children.get(node.node_id, [])
            if not children:
                h = node.rect.height()
            else:
                h = sum(compute_height(c) for c in children) + SIBLING_GAP * (len(children) - 1)
                h = max(h, node.rect.height())
            subtree_height[node.node_id] = h
            return h

        for child in root_children:
            compute_height(child)

        # Répartition équilibrée des branches principales entre gauche et droite, en se basant
        # sur la hauteur totale de chaque sous-arbre (pas seulement leur nombre), pour éviter
        # qu'un côté ne devienne beaucoup plus long que l'autre.
        sorted_children = sorted(root_children, key=lambda n: subtree_height[n.node_id], reverse=True)
        left_children, right_children = [], []
        left_total, right_total = 0.0, 0.0
        for child in sorted_children:
            if left_total <= right_total:
                left_children.append(child)
                left_total += subtree_height[child.node_id] + SIBLING_GAP
            else:
                right_children.append(child)
                right_total += subtree_height[child.node_id] + SIBLING_GAP

        # Largeur de colonne par profondeur relative (1 = branches principales), et espacement
        # minimal requis APRÈS chaque colonne (indexé par la profondeur du nœud source), pour
        # chaque côté — élargi si une des branches qui en partent porte un libellé.
        def compute_level_widths(node, depth, level_width, gap_after):
            level_width[depth] = max(level_width.get(depth, 0), node.rect.width())
            for child in tree_children.get(node.node_id, []):
                needed = max(LEVEL_GAP, label_extra_gap(child))
                gap_after[depth] = max(gap_after.get(depth, LEVEL_GAP), needed)
                compute_level_widths(child, depth + 1, level_width, gap_after)

        def build_level_x(children_group):
            level_width = {}
            gap_after = {0: max(LEVEL_GAP, max((label_extra_gap(c) for c in children_group), default=0))}
            for child in children_group:
                compute_level_widths(child, 1, level_width, gap_after)
            level_x = {}
            cumulative = root.rect.width() / 2 + gap_after[0]
            for depth in sorted(level_width.keys()):
                level_x[depth] = cumulative
                cumulative += level_width[depth] + gap_after.get(depth, LEVEL_GAP)
            return level_x

        right_level_x = build_level_x(right_children)
        left_level_x = build_level_x(left_children)

        def assign_positions(node, depth, top_y, level_x, direction):
            x = direction * (level_x[depth] + node.rect.width() / 2)
            h = subtree_height[node.node_id]
            y = top_y + h / 2
            node.setPos(x, y)

            child_top = top_y
            for child in tree_children.get(node.node_id, []):
                child_h = subtree_height[child.node_id]
                assign_positions(child, depth + 1, child_top, level_x, direction)
                child_top += child_h + SIBLING_GAP

        def layout_side(children_group, level_x, direction):
            total_height = sum(subtree_height[c.node_id] for c in children_group)
            total_height += SIBLING_GAP * max(0, len(children_group) - 1)
            top = -total_height / 2
            for child in children_group:
                h = subtree_height[child.node_id]
                assign_positions(child, 1, top, level_x, direction)
                top += h + SIBLING_GAP

        root.setPos(0, 0)
        layout_side(right_children, right_level_x, 1)
        layout_side(left_children, left_level_x, -1)

        for item in ws.scene.items():
            if isinstance(item, EdgeItem) and hasattr(item, 'update_position'):
                item.update_position()

        self.app.save_state()

        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.center_on_graph()

    def add_child_node(self, parent_node):
        """Ajoute un nœud enfant lié au nœud parent fourni et lance l'édition immédiate."""
        ws = self.app.current_workspace()
        if not ws or not parent_node: return

        # Un nœud plié qui reçoit un nouvel enfant se déplie : sinon le nouveau nœud
        # apparaîtrait immédiatement caché, ce qui serait très déroutant.
        if getattr(parent_node, 'is_collapsed', False):
            parent_node.is_collapsed = False
            self.refresh_fold_visibility()

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
        
        # On force l'état visuel du lien dès sa création
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
        """Calcule l'emplacement le plus proche autour du parent en testant les 4 directions."""
        ws = self.app.current_workspace()
        if not ws or not parent_node:
            return 150, 0

        p_pos = parent_node.pos()
        p_rect = parent_node.rect if hasattr(parent_node, 'rect') else QRectF(-50, -20, 100, 40)
        
        # Marge de la branche (espace suffisant pour laisser passer le lien/arête)
        margin_x = 70
        margin_y = 50

        # Récupération de tous les autres nœuds pour détecter les collisions
        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem) and i != parent_node]

        # 4 directions candidates à tester autour du parent (Droites, Gauche, Bas, Haut)
        candidates = [
            # Droite
            QPointF(p_pos.x() + (p_rect.width() / 2) + margin_x + 50, p_pos.y()),
            # Gauche
            QPointF(p_pos.x() - (p_rect.width() / 2) - margin_x - 50, p_pos.y()),
            # Bas
            QPointF(p_pos.x(), p_pos.y() + (p_rect.height() / 2) + margin_y + 20),
            # Haut
            QPointF(p_pos.x(), p_pos.y() - (p_rect.height() / 2) - margin_y - 20),
        ]

        # Définition des dimensions estimées d'un nouveau nœud
        node_w, node_h = 120, 40

        for pos in candidates:
            cand_rect = QRectF(pos.x() - node_w / 2, pos.y() - node_h / 2, node_w, node_h)
            
            # Vérification de collision avec un autre nœud
            has_collision = False
            for n in all_nodes:
                n_rect = QRectF(n.pos().x() - n.rect.width() / 2, n.pos().y() - n.rect.height() / 2, n.rect.width(), n.rect.height())
                # On ajoute une petite zone de sécurité autour des nœuds existants
                if cand_rect.intersects(n_rect.adjusted(-20, -20, 20, 20)):
                    has_collision = True
                    break

            if not has_collision:
                return pos.x(), pos.y()

        # Si les 4 positions directes sont occupées, on cherche en spirale autour du parent
        angle = 0
        distance = max(p_rect.width(), p_rect.height()) + 80
        while distance < 2000:
            import math
            rad = math.radians(angle)
            test_x = p_pos.x() + distance * math.cos(rad)
            test_y = p_pos.y() + distance * math.sin(rad)
            
            cand_rect = QRectF(test_x - node_w / 2, test_y - node_h / 2, node_w, node_h)
            has_collision = False
            for n in all_nodes:
                n_rect = QRectF(n.pos().x() - n.rect.width() / 2, n.pos().y() - n.rect.height() / 2, n.rect.width(), n.rect.height())
                if cand_rect.intersects(n_rect.adjusted(-20, -20, 20, 20)):
                    has_collision = True
                    break

            if not has_collision:
                return test_x, test_y

            angle += 45
            if angle >= 360:
                angle = 0
                distance += 60

        return p_pos.x() + 150, p_pos.y()

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

    def select_all(self):
        """Sélectionne tous les nœuds et arêtes de la scène active (Ctrl+A)."""
        if hasattr(self.app, 'editing_controller') and getattr(self.app.editing_controller, 'editor', None) is not None:
            return
        ws = self.app.current_workspace()
        if not ws: return
        for item in ws.scene.items():
            if isinstance(item, (NodeItem, EdgeItem)):
                item.setSelected(True)

    def deselect_all(self):
        """Désélectionne tous les éléments de la scène active (Échap)."""
        ws = self.app.current_workspace()
        if not ws: return
        ws.scene.clearSelection()

    def filter_nodes(self, search_text):
        """Filtre visuellement les nœuds de la Mind Map en modifiant leur opacité, en
        cherchant aussi bien dans le libellé que dans le contenu des notes détaillées."""
        ws = self.app.current_workspace()
        if not ws:
            return

        search_text = search_text.lower().strip()
        from graphics.items import NodeItem
        from ui.node_notes_dialog import notes_to_plain_text

        for item in ws.scene.items():
            if isinstance(item, NodeItem):
                if not search_text:
                    item.setOpacity(1.0)
                    continue
                label_match = search_text in item.label.lower()
                notes_match = not label_match and search_text in notes_to_plain_text(getattr(item, 'notes', '')).lower()
                item.setOpacity(1.0 if (label_match or notes_match) else 0.2)