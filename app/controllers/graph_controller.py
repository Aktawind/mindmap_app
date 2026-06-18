# controllers/graph_controller.py
import math
from PyQt6.QtCore import QPointF
from graphics.items import NodeItem, EdgeItem

class GraphController:
    @staticmethod
    def add_child_node(app, parent_node, double_click_handler) -> NodeItem:
        """Crée un nœud enfant relié au nœud parent fourni."""
        ws = app.current_workspace()
        if not ws or not parent_node:
            return None

        # Génération d'un ID unique basé sur l'horodatage ou compteur
        import time
        node_id = f"node_{int(time.time() * 1000)}"

        # Calcul de la position intelligente de l'enfant
        pos = GraphController.calculate_smart_position(parent_node)

        # Choix de la palette de couleur selon le niveau ou le parent
        bg, border = "#60A5FA", "#3B82F6"
        if parent_node.node_id != "root":
            bg, border = parent_node.bg_color.name(), parent_node.border_color.name()

        # Instanciation du nouveau nœud
        child = NodeItem(
            node_id, "Nouveau nœud", pos.x(), pos.y(),
            shape="box", bg=bg, border=border, font_color="#ffffff"
        )
        child.signals.itemDoubleClicked.connect(double_click_handler)
        ws.scene.addItem(child)

        # Création de la branche reliant le parent à l'enfant
        edge_id = f"edge_{int(time.time() * 1000)}"
        edge = EdgeItem(edge_id, parent_node, child, label="", color=border)
        edge.signals.itemDoubleClicked.connect(double_click_handler)
        ws.scene.addItem(edge)

        # Enregistrement dans l'historique
        app.save_state()
        return child

    @staticmethod
    def calculate_smart_position(parent_node) -> QPointF:
        """Calcule un emplacement optimal pour éviter les superpositions de nœuds."""
        parent_pos = parent_node.pos()
        parent_rect = parent_node.boundingRect()

        # On compte les enfants existants pour orienter le nouveau nœud
        existing_children = [
            e.dest_node for e in parent_node.edges 
            if e.source_node == parent_node
        ]
        
        count = len(existing_children)
        distance = 180
        
        if parent_node.node_id == "root":
            # Distribution radiale uniforme autour du nœud racine
            angle = count * (2 * math.pi / 5)  # Pas d'angle par défaut
            dx = distance * math.cos(angle)
            dy = distance * math.sin(angle)
        else:
            # Étalement vertical progressif vers la droite pour les sous-branches
            dx = distance
            dy = (count - (count // 2)) * 60 if count % 2 == 1 else -(count // 2) * 60

        return QPointF(parent_pos.x() + dx, parent_pos.y() + dy)

    @staticmethod
    def delete_selected(app):
        """Supprime tous les éléments (nœuds et branches) actuellement sélectionnés."""
        ws = app.current_workspace()
        if not ws:
            return

        selected_items = ws.scene.selectedItems()
        if not selected_items:
            return

        # On sépare les branches et les nœuds pour éviter les conflits de suppression
        nodes_to_delete = [i for i in selected_items if isinstance(i, NodeItem)]
        edges_to_delete = [i for i in selected_items if isinstance(i, EdgeItem)]

        # Interdiction de supprimer le nœud racine principal
        for node in nodes_to_delete:
            if node.node_id == "root":
                return

        # 1. Suppression des branches sélectionnées
        for edge in edges_to_delete:
            ws.scene.removeItem(edge)

        # 2. Suppression des nœuds et de TOUTES leurs branches rattachées
        for node in nodes_to_delete:
            # On copie la liste car removeItem modifie l'état de node.edges en tâche de fond
            attached_edges = list(node.edges)
            for edge in attached_edges:
                ws.scene.removeItem(edge)
            ws.scene.removeItem(node)

        app.save_state()
        app.on_selection_changed()

    @staticmethod
    def connect_selected_nodes(app, double_click_handler):
        """Relie deux nœuds sélectionnés de manière arbitraire (Cross-link)."""
        ws = app.current_workspace()
        if not ws:
            return

        selected_nodes = [i for i in ws.scene.selectedItems() if isinstance(i, NodeItem)]
        if len(selected_nodes) != 2:
            return  # Il faut exactement deux nœuds sélectionnés

        source, dest = selected_nodes[0], selected_nodes[1]
        
        # Vérification si un lien direct existe déjà pour éviter les doublons
        for edge in source.edges:
            if (edge.source_node == source and edge.dest_node == dest) or \
               (edge.source_node == dest and edge.dest_node == source):
                return

        import time
        edge_id = f"edge_cross_{int(time.time() * 1000)}"
        
        # Création du lien transversal (Cross-link)
        edge = EdgeItem(edge_id, source, dest, label="", color="#A0AEC0")
        edge.signals.itemDoubleClicked.connect(double_click_handler)
        ws.scene.addItem(edge)

        app.save_state()