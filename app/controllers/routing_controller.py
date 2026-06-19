import json
import os

from PyQt6.QtWidgets import QMessageBox, QFileDialog
from ui.selection_manager import on_selection_changed
from graphics.items import NodeItem, EdgeItem

class RoutingController:
    def __init__(self, app):
        self.app = app

    def update_routing_button_ui(self):
        if self.app.btn_toggle_routing.isChecked():
            self.app.btn_toggle_routing.setText("Liens courbes")
        else:
            self.app.btn_toggle_routing.setText("Liens droits")

    def toggle_line_routing(self, checked):
        """Bascule le mode de routage des lignes en fonction de l'état du bouton."""
        ws = self.app.tabs.currentWidget()
        if ws and hasattr(ws, 'scene'):
            # Si coché -> 'curved' (courbe), sinon -> 'orthogonal' (lignes droites/perpendiculaires)
            ws.scene.line_routing_mode = 'curved' if checked else 'orthogonal'
            
            # Met à jour le texte et le helper du bouton
            self.update_routing_button_ui()
            
            # Force chaque ligne à recalculer son tracé
            from graphics.items import EdgeItem
            for item in ws.scene.items():
                if isinstance(item, EdgeItem):
                    item.update_position()
            
            # Rafraîchit l'affichage de la scène
            ws.scene.update()

    def on_arrow_combo_changed(self, index):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            sel[0].arrow_dir = self.app.arrow_combo.itemData(index)
            sel[0].update()
            self.app.save_state()