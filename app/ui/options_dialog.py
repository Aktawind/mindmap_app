from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QSpinBox, QLabel, QDialogButtonBox
from graphics import items
from graphics.items import NodeItem
from ui import theme


def load_preferences(app_window):
    """Applique au démarrage les préférences globales enregistrées (Fichier > Options)."""
    items.set_max_chars_per_line(
        app_window.settings.value("max_chars_per_line", items.MAX_CHARS_PER_LINE, type=int)
    )


def _refresh_all_nodes(app_window):
    """Redimensionne tous les nœuds de tous les onglets ouverts après un changement de
    préférence touchant à leur mise en page (retour à la ligne automatique...)."""
    tabs = getattr(app_window, 'tabs', None)
    if tabs is None:
        return
    for i in range(tabs.count()):
        ws = tabs.widget(i)
        if ws is None or not hasattr(ws, 'scene'):
            continue
        for item in ws.scene.items():
            if isinstance(item, NodeItem):
                item.recalculate_size()
                item.update()
        ws.scene.update()


def show_options_dialog(app_window):
    dialog = QDialog(app_window)
    dialog.setWindowTitle("Options")
    dialog.setMinimumWidth(380)
    layout = QVBoxLayout(dialog)

    form = QFormLayout()
    chars_spin = QSpinBox(dialog)
    chars_spin.setRange(items.MIN_CHARS_PER_LINE, items.MAX_CHARS_PER_LINE_LIMIT)
    chars_spin.setSuffix(" caractères")
    chars_spin.setValue(items.get_max_chars_per_line())
    form.addRow("Retour à la ligne après :", chars_spin)
    layout.addLayout(form)

    hint = QLabel(
        f"Nombre maximal de caractères par ligne dans un nœud avant le retour à la ligne "
        f"automatique. S'applique à toutes les cartes (par défaut : {items.MAX_CHARS_PER_LINE}).",
        dialog
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(f"color: {theme.get_palette(app_window)['text_muted']}; font-size: 11px;")
    layout.addWidget(hint)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    new_value = chars_spin.value()
    if new_value != items.get_max_chars_per_line():
        app_window.settings.setValue("max_chars_per_line", new_value)
        items.set_max_chars_per_line(new_value)
        _refresh_all_nodes(app_window)
