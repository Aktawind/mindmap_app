import json
import os
import sys
from PyQt6.QtCore import QUrl, Qt, QObject
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QTextEdit, QWidget
from graphics.items import NodeItem, EdgeItem
from ui.selection_manager import on_selection_changed

class EditingController(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.edit_item = None
        self.editor = None

    def start_inline_editing(self, item):
        ws = self.app.current_workspace()
        if not ws: return
        
        # Sécurité : si une édition est déjà en cours, on la valide
        if self.editor:
            self.commit_edit()

        self.edit_item = item
        self.editor = QTextEdit(ws.view)
        
        if isinstance(item, NodeItem):
            clean_text = item.label.replace('🚨 ', '').replace('⏳ ', '').replace('✅ ', '')
            view_pos = ws.view.mapFromScene(item.pos())
            w = int(item.rect.width())
            h = max(int(item.rect.height()), 40)
            self.editor.setGeometry(view_pos.x() - w//2, view_pos.y() - h//2, w, h)
        else:
            clean_text = item.label
            center = item.path().pointAtPercent(0.5)
            view_pos = ws.view.mapFromScene(center)
            self.editor.setGeometry(view_pos.x() - 75, view_pos.y() - 15, 150, 40)

        self.editor.setText(clean_text) 
        self.editor.setStyleSheet("border: 2px solid #60A5FA; background: white; font-family: Segoe UI; font-size: 11pt;")
        self.editor.selectAll()
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.editor.show()
        self.editor.setFocus()
        
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == getattr(self, 'editor', None):
            if event.type() == event.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.commit_edit()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.cancel_edit()
                    return True
            elif event.type() == event.Type.FocusOut:
                self.commit_edit()
                return True
        return super().eventFilter(obj, event)

    def commit_edit(self):
        if not self.editor or not self.edit_item: return
        
        new_text = self.editor.toPlainText().strip()
        changed = False
        
        if isinstance(self.edit_item, NodeItem):
            # Réinjecter le préfixe de statut s'il existait
            prefix = ""
            if self.edit_item.status == "urgent": prefix = "🚨 "
            elif self.edit_item.status == "progress": prefix = "⏳ "
            elif self.edit_item.status == "done": prefix = "✅ "
            
            full_text = prefix + new_text
            if new_text and self.edit_item.label != full_text:
                self.edit_item.label = full_text
                # Note : Utilisez update_geometry() ou recalculate_size() selon le nom exact dans votre NodeItem
                if hasattr(self.edit_item, 'update_geometry'):
                    self.edit_item.update_geometry()
                elif hasattr(self.edit_item, 'recalculate_size'):
                    self.edit_item.recalculate_size()
                
                if hasattr(self.edit_item, 'update_edges'):
                    self.edit_item.update_edges()
                changed = True
        else:
            if self.edit_item.label != new_text:
                self.edit_item.label = new_text
                self.edit_item.update()
                changed = True
            
        # Nettoyage propre
        self.editor.removeEventFilter(self)
        self.editor.deleteLater()
        self.editor = None
        
        # Optionnel : Désélectionner le nœud après modification si désiré
        # self.edit_item.setSelected(False)
        self.edit_item = None

        if changed:
            self.app.save_state() 
            
        on_selection_changed(self.app) # Force le rafraîchissement des barres d'outils

    def cancel_edit(self):
        """ Annule l'édition sans sauvegarder les modifications """
        if self.editor:
            self.editor.removeEventFilter(self)
            self.editor.deleteLater()
        self.editor = None
        self.edit_item = None
        on_selection_changed(self.app)

    def on_tab_pressed(self):
        if self.editor is not None: return
        ws = self.app.current_workspace() # CORRECTION : self.app
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            if hasattr(self, 'graph_controller'):
                self.graph_controller.add_child_node(sel[0])
            elif hasattr(self.app, 'graph_controller'):
                self.app.graph_controller.add_child_node(sel[0])

    def edit_selected_edge(self): 
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            self.editing_controller.start_inline_editing(sel[0])