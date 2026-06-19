from PyQt6.QtGui import QColor
from graphics.items import NodeItem

class StyleController:
    def __init__(self, app):
        self.app = app

    def change_color(self, color, border):
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            # Sécurité anti-boucle infinie partagée pour l'ensemble du traitement
            visited = set()
            for node in nodes:
                self.apply_color_downward(node, color, border, visited)
            
            self.app.save_state()

    def apply_color_downward(self, node, bg_color, border_color, visited=None):
        """Applique la couleur au nœud et descend récursivement en évitant les boucles cycliques."""
        if not node:
            return
        
        if visited is None:
            visited = set()
            
        # SÉCURITÉ ANTI-BOUCLE : Si le nœud a déjà été recoloré dans ce cycle, on s'arrête
        if node.node_id in visited:
            return
        visited.add(node.node_id)

        # 1. On applique la couleur au nœud actuel
        node.bg_color = QColor(bg_color)
        node.border_color = QColor(border_color)
        node.update()

        # 2. On parcourt toutes les branches connectées à ce nœud
        if hasattr(node, 'edges') and node.edges:
            for edge in node.edges:
                # Sécurité : on vérifie que le nœud actuel est bien la SOURCE du lien
                if getattr(edge, 'source_node', None) == node and getattr(edge, 'dest_node', None):
                    edge.color = QColor(border_color)
                    edge.update()
                    
                    # Appel récursif sécurisé sur le nœud destination (l'enfant)
                    self.apply_color_downward(edge.dest_node, bg_color, border_color, visited)

    def toggle_bold(self):
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            any_not_bold = any(not getattr(node, 'is_bold', False) for node in nodes)
            target_bold = any_not_bold
            
            for node in nodes:
                node.is_bold = target_bold
                node.update()
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                
            self.app.save_state()

    def on_shape_combo_changed(self, index):
        ws = self.app.current_workspace()
        if not ws or index < 0: return
        
        if not hasattr(self.app, 'shape_combo') or self.app.shape_combo is None: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            for node in nodes:
                node.shape_type = self.app.shape_combo.itemData(index)
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
                
                # CORRECTION : On force les arêtes à se réaligner sur la nouvelle forme
                if hasattr(node, 'edges'):
                    for edge in node.edges:
                        if hasattr(edge, 'update_position'): edge.update_position()
                        elif hasattr(edge, 'update_path'): edge.update_path()
                        edge.update()
                        
            self.app.save_state()

    def on_status_combo_changed(self, index):
        ws = self.app.current_workspace()
        if not ws or index < 0: return
        
        if not hasattr(self.app, 'status_combo') or self.app.status_combo is None: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            status_value = self.app.status_combo.itemData(index)
            
            # Map des emojis pour éviter les nettoyages de chaînes approximatifs
            status_emojis = {"urgent": "🚨 ", "progress": "⏳ ", "done": "✅ ", "none": ""}
            new_emoji = status_emojis.get(status_value, "")

            for node in nodes:
                # On nettoie proprement l'ancien emoji s'il existe au tout début du label
                label = getattr(node, 'label', '')
                for prefix in status_emojis.values():
                    if prefix and label.startswith(prefix):
                        label = label[len(prefix):]
                        break
                
                # On applique le nouveau statut et le nouveau préfixe visuel
                node.status = status_value
                node.label = f"{new_emoji}{label}"
                
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
                
                # Alignement des arêtes suite au changement de taille provoqué par l'emoji
                if hasattr(node, 'edges'):
                    for edge in node.edges:
                        if hasattr(edge, 'update_position'): edge.update_position()
                        edge.update()
                        
            self.app.save_state()