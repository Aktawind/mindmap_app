from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt


def _focus_search_field(app_window):
    """Donne le focus au champ de recherche existant et sélectionne son contenu."""
    search_input = getattr(app_window, 'search_input', None)
    if search_input is None:
        return
    search_input.setFocus()
    search_input.selectAll()


def setup_app_shortcuts(app_window):
    """Définit et attache les raccourcis clavier globaux à la fenêtre principale."""
    app_window.shortcut_tab = QShortcut(QKeySequence(Qt.Key.Key_Tab), app_window)
    app_window.shortcut_tab.activated.connect(app_window.editing_controller.on_tab_pressed)

    app_window.shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), app_window)
    app_window.shortcut_del.activated.connect(app_window.graph_controller.delete_selected)

    app_window.shortcut_bs = QShortcut(QKeySequence(Qt.Key.Key_Backspace), app_window)
    app_window.shortcut_bs.activated.connect(app_window.graph_controller.delete_selected)

    app_window.shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), app_window)
    app_window.shortcut_select_all.activated.connect(app_window.graph_controller.select_all)

    app_window.shortcut_deselect = QShortcut(QKeySequence(Qt.Key.Key_Escape), app_window)
    app_window.shortcut_deselect.activated.connect(app_window.graph_controller.deselect_all)

    app_window.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), app_window)
    app_window.shortcut_search.activated.connect(lambda: _focus_search_field(app_window))