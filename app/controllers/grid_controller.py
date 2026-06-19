from graphics.items import NodeItem

class GridController:
    def __init__(self, app):
        self.app = app

    def toggle_snap_to_grid(self, checked):
        """Active ou désactive l'alignement automatique sur une grille de 20px."""
        ws = self.app.current_workspace()
        # SÉCURITÉ : Évite le crash si aucun espace de travail n'est actif
        if not ws or not hasattr(ws, 'scene') or ws.scene is None: 
            return
            
        ws.scene.snap_to_grid = checked
        
        if checked:
            changed = False
            for item in ws.scene.items():
                if isinstance(item, NodeItem):
                    old_pos = item.pos()
                    # Calcul du calage sur la grille de 20px
                    x = round(old_pos.x() / 20) * 20
                    y = round(old_pos.y() / 20) * 20
                    
                    # On n'applique et ne sauvegarde que si le nœud a effectivement bougé
                    if old_pos.x() != x or old_pos.y() != y:
                        item.setPos(x, y)
                        
                        # CORRECTION : On force la mise à jour des lignes connectées au nœud
                        if hasattr(item, 'update_edges'):
                            item.update_edges()
                        elif hasattr(item, 'update_geometry'):
                            item.update_geometry()
                            
                        changed = True
            
            if changed:
                ws.scene.update()
                self.app.save_state()