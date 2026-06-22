def on_selection_changed(app) -> None:
    """
    Gère la mise à jour et l'affichage contextuel de la barre de style
    en fonction des éléments sélectionnés (Nœuds, Branches) dans le Workspace.
    """
    # Importations locales pour s'assurer que les types sont reconnus sans imports circulaires
    from graphics.items import NodeItem, EdgeItem

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
            if hasattr(app, 'style_bar') and app.style_bar:
                app.style_bar.hide()
        except RuntimeError:
            pass
        return

    # Extraction et filtrage robuste par type d'élément
    selected_nodes = [item for item in sel if isinstance(item, NodeItem)]
    selected_edges = [item for item in sel if isinstance(item, EdgeItem)]
    
    # 1. Affichage de la barre principale si au moins un élément valide est sélectionné
    if selected_nodes or selected_edges:
        if hasattr(app, 'style_bar') and app.style_bar:
            app.style_bar.show()
    else:
        if hasattr(app, 'style_bar') and app.style_bar:
            app.style_bar.hide()
        return

    # 🟢 GESTION DYNAMIQUE DU BOUTON "RELIER"
    # Activé uniquement si l'utilisateur a sélectionné EXACTEMENT 2 nœuds (et rien d'autre)
    if len(selected_nodes) == 2 and len(sel) == 2:
        if hasattr(app, 'connect_controls') and app.connect_controls:
            app.connect_controls.show()
    else:
        if hasattr(app, 'connect_controls') and app.connect_controls:
            app.connect_controls.hide()

    # 🎨 GESTION DE LA PALETTE DE STYLE CONTEXTUELLE
    # Priorité aux nœuds : s'il y a au moins un nœud sélectionné, on affiche les contrôles de nœud
    if selected_nodes:
        if hasattr(app, 'node_controls') and app.node_controls:
            app.node_controls.show()
        if hasattr(app, 'edge_controls') and app.edge_controls:
            app.edge_controls.hide()
        
        # On base les valeurs graphiques sur le premier nœud de la liste de sélection
        target_node = selected_nodes[0]
        
        # 🟢 GESTION DYNAMIQUE ET VISUELLE DES BOUTONS OUVRIR / DISSOCIER
        is_active = bool(hasattr(target_node, 'attachments') and target_node.attachments)
        
        if hasattr(app, 'btn_open') and app.btn_open:
            app.btn_open.setVisible(is_active)
            app.btn_open.setEnabled(is_active)
            
        if hasattr(app, 'btn_detach') and app.btn_detach:
            app.btn_detach.setVisible(is_active)
            app.btn_detach.setEnabled(is_active)

        if hasattr(app, 'style_bar') and app.style_bar:
            layout = app.style_bar.layout()
            if layout:
                layout.activate()  # Force le recalcul immédiat de l'espace occupé par les widgets visibles
                
            # Ajuste la taille physique de la barre pour qu'elle s'adapte au plus près de son contenu (évite le blanc à droite)
            app.style_bar.adjustSize()
        
        if hasattr(app, 'shape_combo') and app.shape_combo:
            app.shape_combo.blockSignals(True)
            app.shape_combo.setCurrentIndex(app.shape_combo.findData(getattr(target_node, 'shape_type', '')))
            app.shape_combo.blockSignals(False)
        
        if hasattr(app, 'status_combo') and app.status_combo:
            app.status_combo.blockSignals(True)
            app.status_combo.setCurrentIndex(app.status_combo.findData(getattr(target_node, 'status', '')))
            app.status_combo.blockSignals(False)
            
    elif selected_edges:
        # S'il n'y a pas de nœud mais au moins une branche
        if hasattr(app, 'node_controls') and app.node_controls:
            app.node_controls.hide()
        if hasattr(app, 'edge_controls') and app.edge_controls:
            app.edge_controls.show()
        
        target_edge = selected_edges[0]
        if hasattr(app, 'arrow_combo') and app.arrow_combo:
            app.arrow_combo.blockSignals(True)
            app.arrow_combo.setCurrentIndex(app.arrow_combo.findData(getattr(target_edge, 'arrow_dir', '')))
            app.arrow_combo.blockSignals(False)
            
    # Repositionnement physique de la barre au-dessus de la sélection
    if hasattr(app, 'reposition_style_bar'):
        app.reposition_style_bar()