from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QLabel, QDialogButtonBox, QFontComboBox,
    QComboBox, QGroupBox
)
from graphics import items
from graphics.items import NodeItem
from ui import theme
from ui.notes_editor import (
    FONT_SIZES, DEFAULT_NOTES_FONT_FAMILY, DEFAULT_NOTES_FONT_SIZE, notes_default_font
)


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
    muted_style = f"color: {theme.get_palette(app_window)['text_muted']}; font-size: 11px;"

    nodes_box = QGroupBox("Nœuds", dialog)
    nodes_layout = QVBoxLayout(nodes_box)
    form = QFormLayout()
    chars_spin = QSpinBox(dialog)
    chars_spin.setRange(items.MIN_CHARS_PER_LINE, items.MAX_CHARS_PER_LINE_LIMIT)
    chars_spin.setSuffix(" caractères")
    chars_spin.setValue(items.get_max_chars_per_line())
    form.addRow("Retour à la ligne après :", chars_spin)
    nodes_layout.addLayout(form)

    hint = QLabel(
        f"Nombre maximal de caractères par ligne dans un nœud avant le retour à la ligne "
        f"automatique. S'applique à toutes les cartes (par défaut : {items.MAX_CHARS_PER_LINE}).",
        dialog
    )
    hint.setWordWrap(True)
    hint.setStyleSheet(muted_style)
    nodes_layout.addWidget(hint)
    layout.addWidget(nodes_box)

    notes_box = QGroupBox("Notes", dialog)
    notes_layout = QVBoxLayout(notes_box)
    notes_form = QFormLayout()
    current_font = notes_default_font(app_window.settings)
    font_combo = QFontComboBox(dialog)
    font_combo.setCurrentFont(current_font)
    notes_form.addRow("Police par défaut :", font_combo)

    size_combo = QComboBox(dialog)
    for size in FONT_SIZES:
        size_combo.addItem(f"{size} pt", size)
    size_index = size_combo.findData(current_font.pointSize())
    size_combo.setCurrentIndex(size_index if size_index >= 0 else FONT_SIZES.index(DEFAULT_NOTES_FONT_SIZE))
    notes_form.addRow("Taille par défaut :", size_combo)
    notes_layout.addLayout(notes_form)

    notes_hint = QLabel(
        f"Police utilisée pour écrire les nouvelles notes. Les notes déjà rédigées gardent "
        f"leur mise en forme (par défaut : {DEFAULT_NOTES_FONT_FAMILY}, {DEFAULT_NOTES_FONT_SIZE} pt).",
        dialog
    )
    notes_hint.setWordWrap(True)
    notes_hint.setStyleSheet(muted_style)
    notes_layout.addWidget(notes_hint)
    layout.addWidget(notes_box)

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

    app_window.settings.setValue("notes_font_family", font_combo.currentFont().family())
    app_window.settings.setValue("notes_font_size", size_combo.currentData())
