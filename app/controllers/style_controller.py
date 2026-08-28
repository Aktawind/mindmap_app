import json
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QColorDialog, QPushButton
from graphics.items import NodeItem, compute_contrast_font_color

class StyleController:
    def __init__(self, app):
        self.app = app
        self._updating_ui = False

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
        node.font_color = QColor(compute_contrast_font_color(bg_color))
        node.update()

        # 2. Descente récursive vers les enfants via les arêtes naturelles
        if hasattr(node, 'edges'):
            for edge in node.edges:
                if getattr(edge, 'source_node', None) == node and hasattr(edge, 'dest_node') and edge.dest_node:
                    self.apply_color_downward(edge.dest_node, bg_color, border_color, visited)

    def load_custom_colors(self):
        raw = self.app.settings.value("custom_node_colors", "[]")
        try:
            colors = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            colors = []
        return colors if isinstance(colors, list) else []

    def save_custom_colors(self, colors):
        self.app.settings.setValue("custom_node_colors", json.dumps(colors))

    def refresh_custom_color_buttons(self):
        layout = getattr(self.app, 'custom_colors_layout', None)
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for hex_color in self.load_custom_colors():
            border = QColor(hex_color).darker(130).name()
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setToolTip("Clic : appliquer  •  Clic droit : supprimer")
            btn.setStyleSheet(f"background: {hex_color}; border: 2px solid {border}; border-radius: 11px;")
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.clicked.connect(lambda checked, c=hex_color, b=border: self.change_color(c, b))
            btn.customContextMenuRequested.connect(lambda pos, c=hex_color: self.remove_custom_color(c))
            layout.addWidget(btn)

    def add_custom_color(self):
        ws = self.app.current_workspace()
        sel = ws.scene.selectedItems() if ws else []
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        initial = nodes[0].bg_color if nodes else QColor('#60A5FA')

        color = QColorDialog.getColor(initial, self.app, "Choisir une couleur personnalisée")
        if not color.isValid():
            return

        hex_color = color.name()
        colors = self.load_custom_colors()
        if hex_color not in colors:
            colors.append(hex_color)
            self.save_custom_colors(colors)
            self.refresh_custom_color_buttons()

        self.change_color(hex_color, color.darker(130).name())

    def remove_custom_color(self, hex_color):
        colors = self.load_custom_colors()
        if hex_color not in colors:
            return
        reply = QMessageBox.question(
            self.app, "Supprimer la couleur",
            "Supprimer cette couleur personnalisée de la palette ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            colors.remove(hex_color)
            self.save_custom_colors(colors)
            self.refresh_custom_color_buttons()

    def toggle_bold(self):
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            for node in nodes:
                node.is_bold = not getattr(node, 'is_bold', False)
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()

    def toggle_italic(self):
        """Bascule le format italique sur les nœuds sélectionnés."""
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if nodes:
            for node in nodes:
                node.is_italic = not getattr(node, 'is_italic', False)
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()

    def toggle_strikethrough(self):
        """Bascule le format barré sur les nœuds sélectionnés."""
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if nodes:
            for node in nodes:
                node.is_strikethrough = not getattr(node, 'is_strikethrough', False)
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()

    def on_shape_combo_changed(self, index):
        if getattr(self, '_updating_ui', False):
            return
            
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            shape_value = self.app.shape_combo.itemData(index)
            for node in nodes:
                node.shape_type = shape_value
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()

    def on_format_combo_changed(self, index):
        if getattr(self, '_updating_ui', False):
            return

        ws = self.app.current_workspace()
        if not ws: return

        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            format_value = self.app.format_combo.itemData(index)
            for node in nodes:
                node.node_format = format_value
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
                if hasattr(node, 'edges'):
                    for edge in node.edges:
                        if hasattr(edge, 'update_position'): edge.update_position()
                        edge.update()
            self.app.save_state()

    def on_status_combo_changed(self, index):
        if getattr(self, '_updating_ui', False):
            return
            
        ws = self.app.current_workspace()
        if not ws: return
        
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

    def on_priority_combo_changed(self, index):
        if getattr(self, '_updating_ui', False):
            return
            
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            priority_value = self.app.priority_combo.itemData(index)
            for node in nodes:
                node.priority = priority_value
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()

    # 🟢 AJOUT : Demande et affectation d'une date d'échéance textuelle
    def prompt_node_date(self):
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if not nodes: return
        
        current_date = getattr(nodes[0], 'date', '') or ''
        
        text, ok = QInputDialog.getText(
            self.app, 
            "Date d'échéance", 
            "Saisissez une échéance (ex: JJ/MM/AAAA) ou laissez vide pour effacer :",
            text=current_date
        )
        
        if ok:
            date_value = text.strip() if text.strip() else None
            for node in nodes:
                node.date = date_value
                if hasattr(node, 'recalculate_size'):
                    node.recalculate_size()
                node.update()
            self.app.save_state()
            # Forcer la mise à jour visuelle immédiate de l'intitulé du bouton
            self.update_toolbar_for_selection(sel)

    # 🟢 AJOUT : Bascule du mode d'affichage compact
    def toggle_compact_mode(self):
        if getattr(self, '_updating_ui', False):
            return
            
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if not nodes: return
        
        is_checked = self.app.btn_compact.isChecked()
        for node in nodes:
            node.is_compact = is_checked
            if hasattr(node, 'recalculate_size'):
                node.recalculate_size()
            node.update()
        self.app.save_state()

    def update_toolbar_for_selection(self, selected_items):
        """Met à jour l'état visuel de tous les boutons de contrôle rattachés à la fenêtre principale."""
        nodes = [i for i in selected_items if isinstance(i, NodeItem)]
        if not nodes:
            return
            
        node = nodes[0]
        self._updating_ui = True
        
        try:
            # Extraction des propriétés du nœud
            shape = getattr(node, 'shape_type', 'box')
            status = getattr(node, 'status', 'none')
            priority = getattr(node, 'priority', 'none')
            is_compact = getattr(node, 'is_compact', False)
            node_date = getattr(node, 'date', None)
            node_format = getattr(node, 'node_format', 'default')

            # 1. Synchronisation de la Forme (Shape)
            if hasattr(self.app, 'shape_combo') and self.app.shape_combo is not None:
                idx = self.app.shape_combo.findData(shape)
                if idx != -1:
                    self.app.shape_combo.setCurrentIndex(idx)

            # 1bis. Synchronisation du Format de nœud
            if hasattr(self.app, 'format_combo') and self.app.format_combo is not None:
                idx = self.app.format_combo.findData(node_format)
                if idx != -1:
                    self.app.format_combo.setCurrentIndex(idx)

            # 2. Synchronisation du Statut
            if hasattr(self.app, 'status_combo') and self.app.status_combo is not None:
                idx = self.app.status_combo.findData(status)
                if idx != -1: 
                    self.app.status_combo.setCurrentIndex(idx)

            # 3. Synchronisation de la Priorité
            if hasattr(self.app, 'priority_combo') and self.app.priority_combo is not None:
                idx = self.app.priority_combo.findData(priority)
                if idx != -1: 
                    self.app.priority_combo.setCurrentIndex(idx)

            # 4. Synchronisation du Mode Compact
            if hasattr(self.app, 'btn_compact') and self.app.btn_compact is not None:
                self.app.btn_compact.setChecked(is_compact)
            
            # 5. Synchronisation de l'Échéance / Date
            if hasattr(self.app, 'btn_set_date') and self.app.btn_set_date is not None:
                if node_date:
                    self.app.btn_set_date.setText(f"📅 {node_date}")
                else:
                    self.app.btn_set_date.setText("📅 Échéance")
                
        finally:
            self._updating_ui = False