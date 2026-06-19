
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
            app.connect_controls.hide()
            if isinstance(sel[0], NodeItem):
                app.node_controls.show()
                app.edge_controls.hide()
                has_links = bool(sel[0].file_path or sel[0].url_link)
                app.btn_open.setVisible(has_links)
                app.btn_detach.setVisible(has_links)
                
                app.shape_combo.blockSignals(True)
                app.shape_combo.setCurrentIndex(app.shape_combo.findData(sel[0].shape_type))
                app.shape_combo.blockSignals(False)
                
                app.status_combo.blockSignals(True)
                app.status_combo.setCurrentIndex(app.status_combo.findData(sel[0].status))
                app.status_combo.blockSignals(False)
                
            elif isinstance(sel[0], EdgeItem):
                app.node_controls.hide()
                app.edge_controls.show()
                
                app.arrow_combo.blockSignals(True)
                app.arrow_combo.setCurrentIndex(app.arrow_combo.findData(sel[0].arrow_dir))
                app.arrow_combo.blockSignals(False)
            app.reposition_style_bar()
        elif len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            app.style_bar.show()
            app.node_controls.hide()
            app.edge_controls.hide()
            app.connect_controls.show()
            app.reposition_style_bar()
        else:
            app.style_bar.hide()