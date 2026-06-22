from graphics.items import NodeItem, EdgeItem

def on_selection_changed(app) -> None:
    """
    Gère la mise à jour et l'affichage contextuel de la barre de style
    en fonction des éléments sélectionnés (Nœuds, Branches) dans le Workspace.
    """
    try:
        if not app or not hasattr(app, 'tabs') or not hasattr(app, 'style_bar'):
            return
        ws = app.current_workspace()
    except RuntimeError:
        # Interception des objets C++ PyQt déjà détruits (ex: fermeture d'onglet)
        return 
        
    if not ws: 
        try:
            if app.style_bar:
                app.style_bar.hide()
        except RuntimeError:
            pass
        return
       
    try:
        sel = ws.scene.selectedItems()
    except RuntimeError:
        return

    if not sel:
        # Rien n'est sélectionné : on cache proprement la barre globale
        try:
            app.style_bar.hide()
        except RuntimeError:
            pass
        return

    # Extraction et filtrage robuste par type d'élément
    selected_nodes = [item for item in sel if isinstance(item, NodeItem)]
    selected_edges = [item for item in sel if isinstance(item, EdgeItem)]
    
    # 1. Affichage de la barre principale si au moins un élément valide est sélectionné
    if selected_nodes or selected_edges:
        app.style_bar.show()
    else:
        app.style_bar.hide()
        return

    # 🟢 GESTION DYNAMIQUE DU BOUTON "RELIER"
    # Activé uniquement si l'utilisateur a sélectionné EXACTEMENT 2 nœuds (et rien d'autre)
    if len(selected_nodes) == 2 and len(sel) == 2:
        app.connect_controls.show()
    else:
        app.connect_controls.hide()

    # 🎨 GESTION DE LA PALETTE DE STYLE CONTEXTUELLE
    # Priorité aux nœuds : s'il y a au moins un nœud sélectionné, on affiche les contrôles de nœud
    if selected_nodes:
        app.node_controls.show()
        app.edge_controls.hide()
        
        # On base les valeurs graphiques sur le premier nœud de la liste de sélection
        target_node = selected_nodes[0]
        
        has_links = bool(getattr(target_node, 'file_path', None) or getattr(target_node, 'url_link', None))
        app.btn_open.setVisible(has_links)
        app.btn_detach.setVisible(has_links)
        
        if hasattr(app, 'shape_combo'):
            app.shape_combo.blockSignals(True)
            app.shape_combo.setCurrentIndex(app.shape_combo.findData(getattr(target_node, 'shape_type', '')))
            app.shape_combo.blockSignals(False)
        
        if hasattr(app, 'status_combo'):
            app.status_combo.blockSignals(True)
            app.status_combo.setCurrentIndex(app.status_combo.findData(getattr(target_node, 'status', '')))
            app.status_combo.blockSignals(False)
            
    elif selected_edges:
        # S'il n'y a pas de nœud mais au moins une branche
        app.node_controls.hide()
        app.edge_controls.show()
        
        target_edge = selected_edges[0]
        if hasattr(app, 'arrow_combo'):
            app.arrow_combo.blockSignals(True)
            app.arrow_combo.setCurrentIndex(app.arrow_combo.findData(getattr(target_edge, 'arrow_dir', '')))
            app.arrow_combo.blockSignals(False)
            
    # Repositionnement physique de la barre au-dessus de la sélection
    if hasattr(app, 'reposition_style_bar'):
        app.reposition_style_bar()