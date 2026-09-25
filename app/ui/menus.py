from PyQt6.QtGui import QKeySequence, QAction
from services.updater_service import check_for_updates
from ui.template_manager_dialog import show_template_manager_dialog
from ui import theme
from ui.minimap import toggle_minimap


def _toggle_shortcuts_overlay(app_window, checked):
    """Affiche/masque l'encart des raccourcis et mémorise le choix de l'utilisateur."""
    if hasattr(app_window, 'overlay') and app_window.overlay is not None:
        app_window.overlay.setVisible(checked)
    app_window.settings.setValue("show_shortcuts_overlay", checked)


def _toggle_dark_mode(app_window, checked):
    """Bascule le thème clair/sombre et réapplique immédiatement les styles."""
    theme.set_dark_mode(app_window, checked)
    theme.apply_theme(app_window)


def _toggle_fold(app_window, checked):
    """Active/désactive globalement le pliage des branches et réapplique immédiatement la
    visibilité sur tous les onglets ouverts (sans perdre les états is_collapsed mémorisés)."""
    app_window.settings.setValue("fold_enabled", checked)
    if hasattr(app_window, 'graph_controller'):
        app_window.graph_controller.refresh_fold_visibility_all_tabs()


def create_menus(app_window):
    """Construit et ajoute les menus à la barre de menus de la fenêtre principale."""
    menu_bar = app_window.menuBar()
    if not menu_bar:
        return

    # ==========================================
    # MENU FICHIER
    # ==========================================
    file_menu = menu_bar.addMenu("Fichier")

    workspace_menu = file_menu.addMenu("Espaces de travail")
    workspace_menu.addAction("📄 Nouvel espace de travail", app_window.workspace_controller.new_workspace)
    workspace_menu.addAction("📂 Ouvrir un espace de travail", app_window.workspace_controller.load_workspace)

    file_menu.addSeparator()
    
    file_menu.addAction("📄 Nouveau mindmap", lambda: app_window.project_service.new_project())
    file_menu.addAction("📂 Ouvrir un mindmap", app_window.project_service.load_project)
    file_menu.addAction("📝 Importer Markdown", app_window.import_controller.import_markdown)

    # Sécurisation des actions avec raccourcis (on évite le chaînage destructeur de pointeur)
    save_action = QAction("💾 Enregistrer", app_window)
    save_action.setShortcut(QKeySequence("Ctrl+S"))
    save_action.triggered.connect(app_window.project_service.save_project)
    file_menu.addAction(save_action)
    
    file_menu.addAction("💾 Enregistrer sous...", lambda: app_window.project_service.save_project(force_save_as=True))

    # ==========================================
    # MENU ÉDITION
    # ==========================================
    edit_menu = menu_bar.addMenu("Édition")

    edit_menu.addAction("🗂️ Gérer les templates", lambda: show_template_manager_dialog(app_window))
    edit_menu.addSeparator()

    undo_action = QAction("↩️ Annuler", app_window)
    undo_action.setShortcut(QKeySequence("Ctrl+Z"))
    undo_action.triggered.connect(app_window.undo)
    undo_action.setEnabled(False)
    edit_menu.addAction(undo_action)
    app_window.undo_action = undo_action

    redo_action = QAction("↪️ Rétablir", app_window)
    redo_action.setShortcut(QKeySequence("Ctrl+Y"))
    redo_action.triggered.connect(app_window.redo)
    redo_action.setEnabled(False)
    edit_menu.addAction(redo_action)
    app_window.redo_action = redo_action

    edit_menu.addSeparator()

    copy_action = QAction("📋 Copier l'élément", app_window)
    copy_action.setShortcut(QKeySequence("Ctrl+C"))
    copy_action.triggered.connect(app_window.tools_controller.copy_selected)
    edit_menu.addAction(copy_action)

    paste_action = QAction("📥 Coller l'élément", app_window)
    paste_action.setShortcut(QKeySequence("Ctrl+V"))
    paste_action.triggered.connect(app_window.tools_controller.paste_node)
    edit_menu.addAction(paste_action)

    # ==========================================
    # MENU EXPORTER
    # ==========================================
    export_menu = menu_bar.addMenu("Exporter")
    export_menu.addAction("Exporter en PNG", app_window.export_controller.export_png)
    export_menu.addAction("Exporter en PDF", app_window.export_controller.export_pdf)
    export_menu.addAction("Exporter en Markdown  ", app_window.export_controller.export_md)

    # ==========================================
    # MENU AFFICHAGE
    # ==========================================
    display_menu = menu_bar.addMenu("Affichage")
    app_window.display_menu = display_menu
    app_window.action_toggle_shortcuts = display_menu.addAction("Afficher les raccourcis")
    app_window.action_toggle_shortcuts.setCheckable(True)
    app_window.action_toggle_shortcuts.setChecked(True)
    app_window.action_toggle_shortcuts.toggled.connect(lambda checked: _toggle_shortcuts_overlay(app_window, checked))

    app_window.action_toggle_fold = display_menu.addAction("Afficher le pliage des branches")
    app_window.action_toggle_fold.setCheckable(True)
    app_window.action_toggle_fold.setChecked(app_window.settings.value("fold_enabled", True, type=bool))
    app_window.action_toggle_fold.setToolTip("Autoriser le pliage/dépliage des branches depuis la carte")
    app_window.action_toggle_fold.toggled.connect(lambda checked: _toggle_fold(app_window, checked))

    app_window.action_toggle_minimap = display_menu.addAction("Afficher la mini-carte")
    app_window.action_toggle_minimap.setCheckable(True)
    app_window.action_toggle_minimap.setChecked(app_window.settings.value("show_minimap", False, type=bool))
    app_window.action_toggle_minimap.toggled.connect(lambda checked: toggle_minimap(app_window, checked))

    display_menu.addSeparator()
    app_window.action_toggle_dark_mode = display_menu.addAction("Thème sombre")
    app_window.action_toggle_dark_mode.setCheckable(True)
    app_window.action_toggle_dark_mode.setChecked(theme.is_dark_mode(app_window))
    app_window.action_toggle_dark_mode.toggled.connect(lambda checked: _toggle_dark_mode(app_window, checked))

    # ==========================================
    # MENU À PROPOS
    # ==========================================
    about_menu = menu_bar.addMenu("À propos")
    about_menu.addAction("À propos de Mindy", app_window.show_about_dialog)
    about_menu.addAction("Vérifier les mises à jour", lambda: check_for_updates(app_window, silent=False))