from PyQt6.QtWidgets import QMessageBox
from graphics.items import NodeItem
from ui.notes_dialog import NodeNotesDialog
from ui.selection_manager import on_selection_changed


class NotesController:
    def __init__(self, app):
        self.app = app

    def open_notes(self, node=None):
        """Ouvre la fenêtre de notes du nœud donné (ou du nœud sélectionné). Un clic sur un
        lien [[Notion]] enregistre la fiche puis ouvre celle du nœud visé, qui est
        sélectionné et centré sur la carte."""
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

        while node is not None:
            dialog = NodeNotesDialog(self.app, node, ws)
            if dialog.exec():
                self._store_notes(ws, node, dialog.get_text())
            node = dialog.next_node
            if node is not None:
                self._reveal(ws, node)

    def _store_notes(self, ws, node, notes):
        if notes == (getattr(node, 'notes', '') or ''):
            return
        node.notes = notes
        ws.is_dirty = True
        node.recalculate_size()
        if hasattr(node, 'edges'):
            for edge in node.edges:
                if hasattr(edge, 'update_position'):
                    edge.update_position()
        node.update()
        on_selection_changed(self.app)
        self.app.save_state()

    def _reveal(self, ws, node):
        """Sélectionne le nœud, déplie ses ancêtres s'il est dans une branche pliée et le
        centre dans la vue."""
        graph = getattr(self.app, 'graph_controller', None)
        if graph is not None and not node.isVisible():
            parent = graph._find_hierarchy_parent(node)
            unfolded = False
            while parent is not None:
                if getattr(parent, 'is_collapsed', False):
                    parent.is_collapsed = False
                    parent.update()
                    unfolded = True
                parent = graph._find_hierarchy_parent(parent)
            if unfolded:
                graph.refresh_fold_visibility(ws)
                ws.is_dirty = True
                self.app.save_state()
        ws.scene.clearSelection()
        node.setSelected(True)
        ws.view.centerOn(node)
