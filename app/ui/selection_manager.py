def on_selection_changed(app) -> None:
    """
    Gère la mise à jour et l'affichage contextuel du panneau de propriétés
    en fonction des éléments sélectionnés (Nœuds, Branches) dans le Workspace.
    """
    # Importations locales pour s'assurer que les types sont reconnus sans imports circulaires
    from graphics.items import NodeItem, EdgeItem

    try:
        if not app or not hasattr(app, 'tabs') or not hasattr(app, 'style_dock'):
            return
        ws = app.current_workspace()
    except RuntimeError:
        # Interception des objets C++ PyQt déjà détruits (ex: fermeture d'onglet)
        return

    if not ws:
        try:
            if app.style_dock:
                app.style_dock.hide()
        except RuntimeError:
            pass
        return

    try:
        sel = ws.scene.selectedItems()
    except RuntimeError:
        return

    if not sel:
        # Rien n'est sélectionné : on cache proprement le panneau
        try:
            if hasattr(app, 'style_dock') and app.style_dock:
                app.style_dock.hide()
        except RuntimeError:
            pass
        return

    # Extraction et filtrage robuste par type d'élément
    selected_nodes = [item for item in sel if isinstance(item, NodeItem)]
    selected_edges = [item for item in sel if isinstance(item, EdgeItem)]

    # 1. Affichage du panneau si au moins un élément valide est sélectionné
    if selected_nodes or selected_edges:
        if hasattr(app, 'style_dock') and app.style_dock:
            app.style_dock.show()
    else:
        if hasattr(app, 'style_dock') and app.style_dock:
            app.style_dock.hide()
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
        is_active_file = bool(hasattr(target_node, 'attachments') and target_node.attachments)
        is_active_image = bool(hasattr(target_node, 'image_path') and target_node.image_path)

        if hasattr(app, 'btn_open') and app.btn_open:
            app.btn_open.setVisible(is_active_file)
            app.btn_open.setEnabled(is_active_file)

        if hasattr(app, 'btn_detach') and app.btn_detach:
            app.btn_detach.setVisible(is_active_file)
            app.btn_detach.setEnabled(is_active_file)

        if hasattr(app, 'btn_img_h') and app.btn_img_h:
            app.btn_img_h.setVisible(is_active_image)
            app.btn_img_h.setEnabled(is_active_image)

        # --- SYNCHRONISATION DES VALEURS DU NOEUD VERS LES COMBOBOX ---
        if hasattr(app, 'shape_combo') and app.shape_combo:
            app.shape_combo.blockSignals(True)
            app.shape_combo.setCurrentIndex(app.shape_combo.findData(getattr(target_node, 'shape_type', 'box')))
            app.shape_combo.blockSignals(False)

        if hasattr(app, 'format_combo') and app.format_combo:
            app.format_combo.blockSignals(True)
            app.format_combo.setCurrentIndex(app.format_combo.findData(getattr(target_node, 'node_format', 'default')))
            app.format_combo.blockSignals(False)

        if hasattr(app, 'status_combo') and app.status_combo:
            app.status_combo.blockSignals(True)
            app.status_combo.setCurrentIndex(app.status_combo.findData(getattr(target_node, 'status', 'none')))
            app.status_combo.blockSignals(False)

        if hasattr(app, 'priority_combo') and app.priority_combo:
            app.priority_combo.blockSignals(True)
            app.priority_combo.setCurrentIndex(app.priority_combo.findData(getattr(target_node, 'priority', 'none')))
            app.priority_combo.blockSignals(False)

        if hasattr(app, 'btn_compact') and app.btn_compact:
            app.btn_compact.blockSignals(True)
            app.btn_compact.setChecked(getattr(target_node, 'is_compact', False))
            app.btn_compact.blockSignals(False)

        if hasattr(app, 'btn_set_date') and app.btn_set_date:
            node_date = getattr(target_node, 'date', None)
            if node_date:
                app.btn_set_date.setText(f"📅 {node_date}")
            else:
                app.btn_set_date.setText("📅 Échéance")

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
