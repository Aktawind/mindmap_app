from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QInputDialog
)
from services import template_service


class TemplateManagerDialog(QDialog):
    def __init__(self, app_window):
        super().__init__(app_window)
        self.app_window = app_window
        self.setWindowTitle("Gérer les templates")
        self.resize(420, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Templates disponibles :</b>"))

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("➕ Ajouter depuis l'onglet actif")
        self.btn_rename = QPushButton("✏️ Renommer")
        self.btn_replace = QPushButton("🔄 Remplacer par l'onglet actif")
        self.btn_delete = QPushButton("🗑️ Supprimer")
        for btn in (self.btn_add, self.btn_rename, self.btn_replace, self.btn_delete):
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.btn_add.clicked.connect(self.add_template)
        self.btn_rename.clicked.connect(self.rename_template)
        self.btn_replace.clicked.connect(self.replace_template)
        self.btn_delete.clicked.connect(self.delete_template)

        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for filename, display_name in template_service.list_templates():
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, filename)
            self.list_widget.addItem(item)

    def _selected_filename(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Sélection requise", "Sélectionnez un template dans la liste.")
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _current_tab_root_tree(self):
        """Construit l'arbre 'root' (avec cross_links et orphan_nodes à plat) prêt à être sauvegardé comme template.

        Un nœud relié uniquement via "Relier les nœuds" (et non via une branche parent/enfant
        classique) est un "orphan_node" dans le modèle de données : il n'a pas de parent dans
        l'arbre, mais reste bien connecté via un cross_link. On l'inclut donc explicitement dans
        le template, avec ses cross_links, plutôt que de le perdre silencieusement.
        """
        ws = self.app_window.current_workspace()
        if not ws:
            QMessageBox.warning(self, "Aucun onglet", "Aucune mind map n'est actuellement ouverte.")
            return None

        state = self.app_window.serializer.get_state()
        root_tree = state.get("root")
        if not root_tree:
            QMessageBox.warning(self, "Mind map vide", "L'onglet actif ne contient aucun nœud.")
            return None

        root_tree = dict(root_tree)
        root_tree["cross_links"] = state.get("cross_links", [])
        root_tree["orphan_nodes"] = state.get("orphan_nodes", [])
        return root_tree

    def add_template(self):
        root_tree = self._current_tab_root_tree()
        if root_tree is None:
            return

        name, ok = QInputDialog.getText(self, "Nouveau template", "Nom du template :")
        if not ok or not name.strip():
            return

        template_service.add_template_from_state(name.strip(), root_tree)
        template_service.refresh_template_combo(self.app_window)
        self.refresh_list()

    def rename_template(self):
        filename = self._selected_filename()
        if not filename:
            return

        current_name = self.list_widget.currentItem().text()
        name, ok = QInputDialog.getText(self, "Renommer le template", "Nouveau nom :", text=current_name)
        if not ok or not name.strip():
            return

        template_service.rename_template(filename, name.strip())
        template_service.refresh_template_combo(self.app_window)
        self.refresh_list()

    def replace_template(self):
        filename = self._selected_filename()
        if not filename:
            return

        display_name = self.list_widget.currentItem().text()
        reply = QMessageBox.question(
            self, "Remplacer le template",
            f"Remplacer le contenu de '{display_name}' par la mind map de l'onglet actif ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        root_tree = self._current_tab_root_tree()
        if root_tree is None:
            return

        template_service.update_template_content(filename, root_tree)

    def delete_template(self):
        filename = self._selected_filename()
        if not filename:
            return

        display_name = self.list_widget.currentItem().text()
        reply = QMessageBox.question(
            self, "Supprimer le template",
            f"Supprimer définitivement le template '{display_name}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            template_service.delete_template(filename)
            template_service.refresh_template_combo(self.app_window)
            self.refresh_list()


def show_template_manager_dialog(app_window):
    dialog = TemplateManagerDialog(app_window)
    dialog.exec()
