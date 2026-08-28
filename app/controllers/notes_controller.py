from PyQt6.QtWidgets import QMessageBox
from graphics.items import NodeItem
from ui.node_notes_dialog import NodeNotesDialog
from ui.selection_manager import on_selection_changed


class NotesController:
    def __init__(self, app):
        self.app = app

    def open_notes_dialog(self, node=None):
        """Ouvre la fenêtre de notes détaillées pour le nœud donné (ou le nœud sélectionné)."""
        ws = self.app.current_workspace()
        if not ws:
            return

        if node is None:
            sel = ws.scene.selectedItems()
            nodes = [item for item in sel if isinstance(item, NodeItem)]
            if len(nodes) != 1:
                QMessageBox.information(self.app, "Sélection", "Sélectionnez un seul nœud pour éditer ses notes.")
                return
            node = nodes[0]

        dialog = NodeNotesDialog(self.app, node.label, getattr(node, 'notes', ''))
        if dialog.exec():
            node.notes = dialog.get_text()
            ws.is_dirty = True
            node.recalculate_size()
            if hasattr(node, 'edges'):
                for edge in node.edges:
                    if hasattr(edge, 'update_position'):
                        edge.update_position()
            node.update()
            on_selection_changed(self.app)
            self.app.save_state()
