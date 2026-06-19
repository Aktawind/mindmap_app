from PyQt6.QtGui import QKeySequence, QAction

def create_menus(app_window):
    """Construit et ajoute les menus à la barre de menus de la fenêtre principale."""
    menu_bar = app_window.menuBar()
    if not menu_bar:
        return

    # ==========================================
    # MENU FICHIER
    # ==========================================
    file_menu = menu_bar.addMenu("Fichier")
    
    file_menu.addAction("📄 Nouveau mindmap", lambda: app_window.project_service.new_project())
    file_menu.addSeparator()
    file_menu.addAction("📂 Ouvrir un mindmap", app_window.project_service.load_project)
    
    # Sécurisation des actions avec raccourcis (on évite le chaînage destructeur de pointeur)
    save_action = QAction("💾 Enregistrer", app_window)
    save_action.setShortcut(QKeySequence("Ctrl+S"))
    save_action.triggered.connect(app_window.project_service.save_project)
    file_menu.addAction(save_action)
    
    file_menu.addAction("💾 Enregistrer sous...", lambda: app_window.project_service.save_project(force_save_as=True))

    file_menu.addSeparator()
    workspace_menu = file_menu.addMenu("Espaces de travail")
    workspace_menu.addAction("📄 Nouvel espace de travail", app_window.workspace_controller.new_workspace)
    workspace_menu.addAction("📂 Ouvrir un espace de travail", app_window.workspace_controller.load_workspace)
    
    # ==========================================
    # MENU ÉDITION
    # ==========================================
    edit_menu = menu_bar.addMenu("Édition")
    
    undo_action = QAction("↩️ Annuler", app_window)
    undo_action.setShortcut(QKeySequence("Ctrl+Z"))
    undo_action.triggered.connect(app_window.undo)
    edit_menu.addAction(undo_action)
    
    redo_action = QAction("↪️ Rétablir", app_window)
    redo_action.setShortcut(QKeySequence("Ctrl+Y"))
    redo_action.triggered.connect(app_window.redo)
    edit_menu.addAction(redo_action)
    
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
    export_menu.addAction("Exporter en Image PNG", app_window.export_controller.export_png)
    export_menu.addAction("Exporter en PDF Vectoriel", app_window.export_controller.export_pdf)
    export_menu.addAction("Exporter en Markdown", app_window.export_controller.export_md)

    # ==========================================
    # MENU À PROPOS
    # ==========================================
    about_menu = menu_bar.addMenu("À propos")
    about_menu.addAction("À propos de Mindy", app_window.show_about_dialog)