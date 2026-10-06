from PyQt6.QtCore import Qt, QObject
from PyQt6.QtWidgets import QTextEdit
from graphics.items import NodeItem, EdgeItem, TEXT_ALIGNMENTS, DEFAULT_TEXT_ALIGN, get_max_chars_per_line
from ui.selection_manager import on_selection_changed
from ui import theme

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
            # Pas de barre de défilement : la zone de saisie s'agrandit avec le texte (voir
            # _fit_node_editor), en partant du centre horizontal et du bord haut du nœud.
            self._node_editor_anchor = (view_pos.x(), view_pos.y() - h // 2, w, h)
            self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
        elif isinstance(item, EdgeItem):
            clean_text = getattr(item, 'label', "")
            # Sécurité au cas où la méthode path() ou pointAtPercent() échouerait
            try:
                center = item.path().pointAtPercent(0.5)
                view_pos = ws.view.mapFromScene(center)
            except Exception:
                view_pos = ws.view.mapFromScene(item.pos()) if hasattr(item, 'pos') else ws.view.mapFromScene(ws.scene.sceneRect().center())
                
            # Un peu plus haut que le strict nécessaire pour une ligne, afin de pouvoir
            # confortablement saisir un libellé de branche sur plusieurs lignes (Maj+Entrée)
            self.editor.setGeometry(view_pos.x() - 90, view_pos.y() - 25, 180, 60)
        else:
            # Sécurité : Type d'élément non pris en charge pour l'édition
            self.editor.deleteLater()
            self.editor = None
            self.edit_item = None
            return

        self.editor.setText(clean_text)
        # Fond/texte pris sur la palette du thème courant : un fond blanc figé associait un
        # texte clair (couleur du thème sombre) à un fond clair, rendant la saisie invisible.
        p = theme.get_palette(self.app)
        self.editor.setStyleSheet(
            f"border: 2px solid #60A5FA; background: {p['bg_elevated']}; color: {p['text']}; "
            f"font-family: Segoe UI; font-size: 11pt;"
        )
        self.editor.selectAll()
        if isinstance(item, NodeItem):
            self.editor.setAlignment(TEXT_ALIGNMENTS.get(getattr(item, 'text_align', DEFAULT_TEXT_ALIGN),
                                                         Qt.AlignmentFlag.AlignHCenter))
            self.editor.ensurePolished()  # police de la feuille de style appliquée avant la mesure
            self._fit_node_editor()
            self.editor.textChanged.connect(self._fit_node_editor)
        else:
            self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.show()
        self.editor.setFocus()
        
        self.editor.installEventFilter(self)

    def _fit_node_editor(self):
        """Ajuste la zone de saisie d'un nœud à son contenu : elle s'élargit jusqu'à la
        largeur du retour à la ligne automatique (Fichier > Options), puis grandit en hauteur
        au lieu d'afficher une barre de défilement, peu lisible sur un texte long."""
        editor = self.editor
        anchor = getattr(self, '_node_editor_anchor', None)
        if editor is None or anchor is None or not isinstance(self.edit_item, NodeItem):
            return
        center_x, top_y, min_w, min_h = anchor

        fm = editor.fontMetrics()
        doc = editor.document()
        # Bordure du cadre + marges internes du document, de part et d'autre
        chrome = 2 * editor.frameWidth() + 2 * int(doc.documentMargin()) + 4
        max_w = fm.averageCharWidth() * get_max_chars_per_line() + chrome
        longest_line = max((fm.horizontalAdvance(line) for line in editor.toPlainText().split('\n')), default=0)
        w = int(max(min_w, min(longest_line + chrome, max_w)))

        doc.setTextWidth(w - 2 * editor.frameWidth())
        h = int(max(min_h, doc.size().height() + 2 * editor.frameWidth() + 4))

        editor.setGeometry(int(center_x - w // 2), int(top_y), w, h)

    def _insert_emoji_in_editor(self):
        """Ctrl+E pendant la saisie : insère l'emoji choisi à la position du curseur."""
        editor = self.editor
        if editor is None:
            return
        from ui.emoji_picker import pick_emoji
        self._emoji_picker_open = True
        try:
            emoji = pick_emoji(self.app)
        finally:
            self._emoji_picker_open = False
        if self.editor is not editor:
            return  # l'édition a été fermée entre-temps
        if emoji:
            editor.insertPlainText(emoji)
        editor.activateWindow()
        editor.setFocus()

    def eventFilter(self, obj, event):
        """Filtre les événements clavier et de focus pour l'éditeur de texte."""
        if obj == getattr(self, 'editor', None):
            # Réserve Échap/Entrée à l'éditeur pour éviter qu'un raccourci global
            # (ex : Échap = désélectionner) ne les intercepte avant qu'ils n'atteignent le champ
            is_emoji_shortcut = (event.type() in (event.Type.ShortcutOverride, event.Type.KeyPress)
                                 and event.key() == Qt.Key.Key_E
                                 and event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if event.type() == event.Type.ShortcutOverride:
                if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter) or is_emoji_shortcut:
                    event.accept()
                    return True
            if event.type() == event.Type.KeyPress and is_emoji_shortcut:
                self._insert_emoji_in_editor()
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
                # La perte de focus valide automatiquement — sauf quand c'est le sélecteur
                # d'emojis (Ctrl+E) qui prend le focus le temps du choix
                if getattr(self, '_emoji_picker_open', False):
                    return False
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

    def on_enter_pressed(self):
        """Gère l'appui sur Entrée pour insérer un nœud frère au nœud sélectionné, s'il n'y a
        pas d'édition en cours (Entrée y valide déjà l'édition du texte, voir eventFilter)."""
        if self.editor is not None:
            return
        ws = self.app.current_workspace()
        if not ws:
            return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            if hasattr(self.app, 'graph_controller'):
                self.app.graph_controller.add_sibling_node(sel[0])

    def edit_selected_edge(self):
        """Déclenche l'édition sur le lien (EdgeItem) sélectionné."""
        ws = self.app.current_workspace()
        if not ws: 
            return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            # CORRECTION : Remplacement de self.editing_controller par self
            self.start_inline_editing(sel[0])