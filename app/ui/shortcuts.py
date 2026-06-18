# ui/shortcuts.py
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt

def setup_app_shortcuts(app_window):
    """Définit et attache les raccourcis clavier globaux à la fenêtre principale."""
    app_window.shortcut_tab = QShortcut(QKeySequence(Qt.Key.Key_Tab), app_window)
    app_window.shortcut_tab.activated.connect(app_window.on_tab_pressed)
    
    app_window.shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), app_window)
    app_window.shortcut_del.activated.connect(app_window.delete_selected)
    
    app_window.shortcut_bs = QShortcut(QKeySequence(Qt.Key.Key_Backspace), app_window)
    app_window.shortcut_bs.activated.connect(app_window.delete_selected)