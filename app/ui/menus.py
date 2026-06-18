# ui/menus.py
from PyQt6.QtGui import QKeySequence

def create_menus(app_window):
    """Construit et ajoute les menus à la barre de menus de la fenêtre."""
    menu_bar = app_window.menuBar()

    # Menu Fichier
    file_menu = menu_bar.addMenu("Fichier")
    file_menu.addAction("📄 Nouveau mindmap", lambda: app_window.new_project())
    file_menu.addSeparator()
    file_menu.addAction("📂 Ouvrir un mindmap", app_window.load_project)
    file_menu.addAction("💾 Enregistrer", app_window.save_project).setShortcut("Ctrl+S")
    file_menu.addAction("💾 Enregistrer sous...", lambda: app_window.save_project(force_save_as=True))

    file_menu.addSeparator()
    workspace_menu = file_menu.addMenu("Espaces de travail")
    workspace_menu.addAction("📄 Nouvel espace de travail", app_window.new_workspace)
    workspace_menu.addAction("📂 Ouvrir un espace de travail", app_window.load_workspace)
    
    # Menu Édition
    edit_menu = menu_bar.addMenu("Édition")
    edit_menu.addAction("↩️ Annuler", app_window.undo).setShortcut(QKeySequence("Ctrl+Z"))
    edit_menu.addAction("↪️ Rétablir", app_window.redo).setShortcut(QKeySequence("Ctrl+Y"))
    edit_menu.addSeparator()
    edit_menu.addAction("📋 Copier l'élément", app_window.copy_selected).setShortcut(QKeySequence("Ctrl+C"))
    edit_menu.addAction("📥 Coller l'élément", app_window.paste_node).setShortcut(QKeySequence("Ctrl+V"))
    
    # Menu Exporter
    export_menu = menu_bar.addMenu("Exporter")
    export_menu.addAction("Exporter en Image PNG", app_window.export_png)
    export_menu.addAction("Exporter en PDF Vectoriel", app_window.export_pdf)
    export_menu.addAction("Exporter en Markdown", app_window.export_md)

    # Menu À propos
    about_menu = menu_bar.addMenu("À propos")
    about_menu.addAction("À propos de Mindy", app_window.show_about_dialog)