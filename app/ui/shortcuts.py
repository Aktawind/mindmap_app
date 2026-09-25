from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt


def _open_search_bar(app_window, focus_replace=False):
    search_bar = getattr(app_window, 'search_bar', None)
    if search_bar is None:
        return
    search_bar.open_bar(focus_replace=focus_replace)


def setup_app_shortcuts(app_window):
    """Définit et attache les raccourcis clavier globaux à la fenêtre principale."""
    app_window.shortcut_tab = QShortcut(QKeySequence(Qt.Key.Key_Tab), app_window)
    app_window.shortcut_tab.activated.connect(app_window.editing_controller.on_tab_pressed)

    # Entrée = nœud frère (au même niveau), comme dans la plupart des logiciels de mindmap.
    # Sans danger pendant l'édition inline d'un libellé : l'éditeur de texte réserve déjà
    # Entrée/Échap pour lui-même via ShortcutOverride (voir EditingController.eventFilter).
    app_window.shortcut_enter = QShortcut(QKeySequence(Qt.Key.Key_Return), app_window)
    app_window.shortcut_enter.activated.connect(app_window.editing_controller.on_enter_pressed)

    app_window.shortcut_enter_numpad = QShortcut(QKeySequence(Qt.Key.Key_Enter), app_window)
    app_window.shortcut_enter_numpad.activated.connect(app_window.editing_controller.on_enter_pressed)

    app_window.shortcut_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), app_window)
    app_window.shortcut_del.activated.connect(app_window.graph_controller.delete_selected)

    app_window.shortcut_bs = QShortcut(QKeySequence(Qt.Key.Key_Backspace), app_window)
    app_window.shortcut_bs.activated.connect(app_window.graph_controller.delete_selected)

    app_window.shortcut_select_all = QShortcut(QKeySequence("Ctrl+A"), app_window)
    app_window.shortcut_select_all.activated.connect(app_window.graph_controller.select_all)

    app_window.shortcut_deselect = QShortcut(QKeySequence(Qt.Key.Key_Escape), app_window)
    app_window.shortcut_deselect.activated.connect(app_window.graph_controller.deselect_all)

    app_window.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), app_window)
    app_window.shortcut_search.activated.connect(lambda: _open_search_bar(app_window))

    app_window.shortcut_replace = QShortcut(QKeySequence("Ctrl+R"), app_window)
    app_window.shortcut_replace.activated.connect(lambda: _open_search_bar(app_window, focus_replace=True))