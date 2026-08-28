from PyQt6.QtCore import Qt, QObject
from PyQt6.QtWidgets import QTextEdit
from graphics.items import NodeItem, EdgeItem
from ui.selection_manager import on_selection_changed

class EditingController(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.edit_item = None
        self.editor = None

    def start_inline_editing(self, item):
        """Lance l'édition textuelle en place sur un NodeItem ou un EdgeItem."""
        ws = self.app.current_workspace()
        if not ws: 
            return
        
        # Sécurité : si une édition est déjà en cours, on la valide d'abord
        if self.editor:
            self.commit_edit()

        self.edit_item = item
        self.editor = QTextEdit(ws.view)
        
        if isinstance(item, NodeItem):
            # Nettoyage des badges de statut pour ne pas éditer les émojis bruts
            clean_text = getattr(item, 'label', "").replace('🚨 ', '').replace('⏳ ', '').replace('✅ ', '')
            view_pos = ws.view.mapFromScene(item.pos())
            w = int(item.rect.width())
            h = max(int(item.rect.height()), 40)
            self.editor.setGeometry(view_pos.x() - w//2, view_pos.y() - h//2, w, h)
            
        elif isinstance(item, EdgeItem):
            clean_text = getattr(item, 'label', "")
            # Sécurité au cas où la méthode path() ou pointAtPercent() échouerait
            try:
                center = item.path().pointAtPercent(0.5)
                view_pos = ws.view.mapFromScene(center)
            except Exception:
                view_pos = ws.view.mapFromScene(item.pos()) if hasattr(item, 'pos') else ws.view.mapFromScene(ws.scene.sceneRect().center())
                
            self.editor.setGeometry(view_pos.x() - 75, view_pos.y() - 15, 150, 40)
        else:
            # Sécurité : Type d'élément non pris en charge pour l'édition
            self.editor.deleteLater()
            self.editor = None
            self.edit_item = None
            return

        self.editor.setText(clean_text) 
        self.editor.setStyleSheet("border: 2px solid #60A5FA; background: white; font-family: Segoe UI; font-size: 11pt;")
        self.editor.selectAll()
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.editor.show()
        self.editor.setFocus()
        
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Filtre les événements clavier et de focus pour l'éditeur de texte."""
        if obj == getattr(self, 'editor', None):
            # Réserve Échap/Entrée à l'éditeur pour éviter qu'un raccourci global
            # (ex : Échap = désélectionner) ne les intercepte avant qu'ils n'atteignent le champ
            if event.type() == event.Type.ShortcutOverride:
                if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    event.accept()
                    return True
            if event.type() == event.Type.KeyPress:
                # Entrée valide l'édition (sauf si Shift est enfoncé pour un saut de ligne)
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self.commit_edit()
                    return True
                # Échap annule l'édition
                if event.key() == Qt.Key.Key_Escape:
                    self.cancel_edit()
                    return True
            elif event.type() == event.Type.FocusOut:
                # La perte de focus valide automatiquement
                self.commit_edit()
                return True
        return super().eventFilter(obj, event)

    def commit_edit(self):
        """Enregistre les modifications textuelles et ferme l'éditeur."""
        if not self.editor or not self.edit_item: 
            return
        
        # Copie locale des références pour éviter les conflits d'événements pendant la destruction
        editor = self.editor
        item = self.edit_item
        
        # Réinitialisation immédiate des variables d'état (Sécurité anti-boucle)
        self.editor = None
        self.edit_item = None
        
        new_text = editor.toPlainText().strip()
        changed = False
        
        if isinstance(item, NodeItem):
            # Réinjecter le préfixe de statut s'il existait
            prefix = ""
            status = getattr(item, 'status', None)
            if status == "urgent": prefix = "🚨 "
            elif status == "progress": prefix = "⏳ "
            elif status == "done": prefix = "✅ "
            
            full_text = prefix + new_text
            if new_text and item.label != full_text:
                item.label = full_text
                
                if hasattr(item, 'update_geometry'):
                    item.update_geometry()
                elif hasattr(item, 'recalculate_size'):
                    item.recalculate_size()
                
                if hasattr(item, 'update_edges'):
                    item.update_edges()
                changed = True
        elif isinstance(item, EdgeItem):
            if item.label != new_text:
                item.label = new_text
                item.update()
                changed = True
            
        # Nettoyage propre du widget
        editor.removeEventFilter(self)
        editor.deleteLater()
        
        if changed:
            self.app.save_state() 
            
        on_selection_changed(self.app)

    def cancel_edit(self):
        """Annule l'édition en cours sans enregistrer les modifications."""
        if self.editor:
            self.editor.removeEventFilter(self)
            self.editor.deleteLater()
        self.editor = None
        self.edit_item = None
        on_selection_changed(self.app)

    def on_tab_pressed(self):
        """Gère l'appui sur la touche Tab pour insérer un nœud enfant s'il n'y a pas d'édition en cours."""
        if self.editor is not None: 
            return
        ws = self.app.current_workspace()
        if not ws: 
            return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            if hasattr(self, 'graph_controller'):
                self.graph_controller.add_child_node(sel[0])
            elif hasattr(self.app, 'graph_controller'):
                self.app.graph_controller.add_child_node(sel[0])

    def edit_selected_edge(self): 
        """Déclenche l'édition sur le lien (EdgeItem) sélectionné."""
        ws = self.app.current_workspace()
        if not ws: 
            return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            # CORRECTION : Remplacement de self.editing_controller par self
            self.start_inline_editing(sel[0])