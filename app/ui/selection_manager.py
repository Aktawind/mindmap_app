
from graphics.items import NodeItem, EdgeItem

def on_selection_changed(app):
        try:
            if not app or not hasattr(app, 'tabs'):
                return
            ws = app.current_workspace()
        except RuntimeError:
            return # On intercepte le crash C++ direct et on stoppe proprement
            
        if not ws: 
            # Sécurité supplémentaire au cas où les contrôleurs de barre de style seraient déjà détruits
            try:
                if hasattr(app, 'style_bar') and app.style_bar:
                    app.style_bar.hide()
            except RuntimeError:
                pass
            return
           
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if len(sel) >= 1:
            app.style_bar.show()
            
            # 🟢 GESTION DYNAMIQUE DU BOUTON "RELIER"
            # Il s'affiche EN PLUS uniquement si on a exactement 2 nœuds sélectionnés
            if len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
                app.connect_controls.show()
            else:
                app.connect_controls.hide()

            # 🎨 GESTION DE LA PALETTE DE STYLE (BASÉE SUR LE PREMIER ÉLÉMENT)
            if isinstance(sel[0], NodeItem):
                app.node_controls.show()
                app.edge_controls.hide()
                
                has_links = bool(getattr(sel[0], 'file_path', None) or getattr(sel[0], 'url_link', None))
                app.btn_open.setVisible(has_links)
                app.btn_detach.setVisible(has_links)
                
                if hasattr(app, 'shape_combo'):
                    app.shape_combo.blockSignals(True)
                    app.shape_combo.setCurrentIndex(app.shape_combo.findData(getattr(sel[0], 'shape_type', '')))
                    app.shape_combo.blockSignals(False)
                
                if hasattr(app, 'status_combo'):
                    app.status_combo.blockSignals(True)
                    app.status_combo.setCurrentIndex(app.status_combo.findData(getattr(sel[0], 'status', '')))
                    app.status_combo.blockSignals(False)
                
            elif isinstance(sel[0], EdgeItem):
                app.node_controls.hide()
                app.edge_controls.show()
                
                if hasattr(app, 'arrow_combo'):
                    app.arrow_combo.blockSignals(True)
                    app.arrow_combo.setCurrentIndex(app.arrow_combo.findData(getattr(sel[0], 'arrow_dir', '')))
                    app.arrow_combo.blockSignals(False)
                    
            app.reposition_style_bar()
            
        else:
            # Rien n'est sélectionné : on cache tout
            app.style_bar.hide()