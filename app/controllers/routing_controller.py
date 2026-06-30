from graphics.items import EdgeItem

class RoutingController:
    def __init__(self, app):
        self.app = app

    def update_routing_button_ui(self):
        """Ajuste l'état enfoncé/relâché et le texte du bouton selon le mode réel de la scène."""
        if not hasattr(self.app, 'btn_toggle_routing') or self.app.btn_toggle_routing is None:
            return
            
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None:
            return

        # Récupération du mode réel actuel de la scène
        if not hasattr(ws.scene, 'line_routing_mode'):
            is_button_checked = self.app.btn_toggle_routing.isChecked()
            ws.scene.line_routing_mode = 'curved' if is_button_checked else 'orthogonal'
        current_mode = getattr(ws.scene, 'line_routing_mode', 'curved')
        
        self.app.btn_toggle_routing.blockSignals(True)
        # Le bouton reste enfoncé si on est en mode courbe
        self.app.btn_toggle_routing.setChecked(current_mode == 'curved')
        self.app.btn_toggle_routing.blockSignals(False)

        # Synchronisation du texte selon les 4 modes disponibles
        if current_mode == 'curved':
            self.app.btn_toggle_routing.setText("Liens courbes")
        elif current_mode == 'orthogonal':
            self.app.btn_toggle_routing.setText("Liens droits (Coudés)")
        elif current_mode == 'straight_diagonal':
            self.app.btn_toggle_routing.setText("Liens diagonaux")
        elif current_mode == 'straight_elbow':
            self.app.btn_toggle_routing.setText("Liens coudés droits")

    def set_routing_mode(self, mode_string):
        """
        Méthode centralisée pour forcer un mode de routage spécifique.
        Utile lors du changement automatique de Canvas (ex: Concept Map -> straight_diagonal).
        """
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None: 
            return

        if mode_string in ['curved', 'orthogonal', 'straight_diagonal', 'straight_elbow']:
            ws.scene.line_routing_mode = mode_string
            self._apply_routing_to_all_edges(ws)

    def toggle_line_routing(self, checked):
        """Bascule historique du mode de routage (courbes vs orthogonales)."""
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None: 
            return
            
        # Si coché -> 'curved', sinon -> 'orthogonal'
        ws.scene.line_routing_mode = 'curved' if checked else 'orthogonal'
        self._apply_routing_to_all_edges(ws)

    def _apply_routing_to_all_edges(self, workspace):
        """Méthode interne pour recalculer la géométrie de tous les liens de la scène."""
        # Met à jour le texte du bouton ou des menus connectés
        self.update_routing_button_ui()
        
        # Force chaque ligne à recalculer son tracé géométrique
        for item in workspace.scene.items():
            if isinstance(item, EdgeItem):
                if hasattr(item, 'update_position'):
                    item.update_position()
                elif hasattr(item, 'update_path'):
                    item.update_path()
                else:
                    item.update()
        
        # Rafraîchit l'affichage de la scène et sauvegarde l'état
        workspace.scene.update()
        if hasattr(self.app, 'save_state'):
            self.app.save_state()

    def on_arrow_combo_changed(self, index):
        """Gère le changement de direction des flèches sur le lien sélectionné."""
        ws = self.app.current_workspace()
        if not ws or index < 0: 
            return
            
        if not hasattr(self.app, 'arrow_combo') or self.app.arrow_combo is None:
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            # Récupération de la donnée associée à l'index du ComboBox
            sel[0].arrow_dir = self.app.arrow_combo.itemData(index)
            sel[0].update()
            self.app.save_state()