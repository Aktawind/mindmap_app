# controllers/style_controller.py
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog
from graphics.items import NodeItem

class StyleController:
    @staticmethod
    def change_color(app, color, border):
        ws = app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            # On applique la couleur en cascade à CHAQUE nœud sélectionné
            for node in nodes:
                StyleController.apply_color_downward(node, color, border)
            
            # Un seul snapshot de l'état pour tout le groupe
            app.save_state()

    @staticmethod
    def apply_color_downward(node, bg_color, border_color):
        """Applique la couleur au nœud et descend récursivement vers tous ses enfants."""
        if not node:
            return

        # 1. On applique la couleur au nœud actuel
        node.bg_color = QColor(bg_color)
        node.border_color = QColor(border_color)
        node.update()

        # 2. On parcourt toutes les branches connectées à ce nœud
        for edge in node.edges:
            # Sécurité : on vérifie que le nœud actuel est bien la SOURCE du lien
            # (ce qui garantit qu'on descend vers l'enfant, sans remonter vers le parent)
            if edge.source_node == node:
                # Optionnel : Si vous souhaitez aussi recolorer le trait de la branche
                edge.color = QColor(border_color)
                edge.update()
                
                # Appel récursif sur le nœud destination (l'enfant)
                StyleController.apply_color_downward(edge.dest_node, bg_color, border_color)

    @staticmethod
    def toggle_bold(app):
        ws = app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            # Règle d'or : si au moins un nœud n'est pas en gras, on applique le gras à tous.
            # Sinon, on désactive le gras pour tous.
            any_not_bold = any(not node.is_bold for node in nodes)
            target_bold = any_not_bold
            
            for node in nodes:
                node.is_bold = target_bold
                node.update()
                
            app.save_state()

    @staticmethod
    def on_shape_combo_changed(app, index):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            for node in nodes:
                node.shape_type = app.shape_combo.itemData(index)
                node.update()
                node.recalculate_size()
            app.save_state()

    @staticmethod
    def on_status_combo_changed(app, index):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            for node in nodes:
                node.label = node.label.replace("🚨 ", "").replace("⏳ ", "").replace("✅ ", "")
                node.status = app.status_combo.itemData(index)
                node.recalculate_size()
                node.update()
            app.save_state()