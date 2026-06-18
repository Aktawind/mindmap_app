# controllers/attachment_controller.py
import os
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from graphics.items import NodeItem

class AttachmentController:
    @staticmethod
    def attach_file(app):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if not ws.current_file_path:
                QMessageBox.information(app, "Sauvegarde requise", "Veuillez d'abord enregistrer votre Mind Map afin de pouvoir y attacher des fichiers.")
                app.save_file()
                if not ws.current_file_path: return # Annulé par l'utilisateur
                
            path, _ = QFileDialog.getOpenFileName(app, "Choisir un document à joindre")
            if path:
                if node.file_path:
                    app.remove_file_from_attachments(ws, node.file_path)
                
                # Copie et récupération du chemin relatif
                relative_dest = app.copy_file_to_attachments(ws, node.node_id, path)
                node.file_path = relative_dest
                node.recalculate_size()
                app.on_selection_changed()
                node.update()
                app.save_state()

    @staticmethod
    def attach_url(app):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            url, ok = QInputDialog.getText(app, "Associer une URL", "Entrez l'adresse internet :", text=node.url_link or "https://")
            if ok and url.strip():
                node.url_link = url.strip()
                node.recalculate_size()
                app.on_selection_changed()
                node.update()
                app.save_state()

    @staticmethod
    def detach_links(app):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]

            if node.file_path:
                # Suppression physique du fichier dans .mindmap_attachments
                app.remove_file_from_attachments(ws, node.file_path)
                node.file_path = None
                node.url_link = None
                node.recalculate_size()
                app.on_selection_changed()
                node.update()
                app.save_state()

    @staticmethod
    def open_file(app):
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            
            # SÉCURITÉ : Si le nœud a une URL mais pas de fichier local,
            # on bascule automatiquement sur l'ouverture de l'URL !
            if not node.file_path and node.url_link:
                AttachmentController.open_url(app)
                return

            if not node.file_path:
                return

            # Si le chemin est relatif, on le recompose à partir du dossier du JSON
            if not os.path.isabs(node.file_path) and ws.current_file_path:
                base_dir = os.path.dirname(ws.current_file_path)
                full_path = os.path.abspath(os.path.join(base_dir, node.file_path))
            else:
                full_path = node.file_path

            if os.path.exists(full_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
            else:
                QMessageBox.warning(app, "Erreur", "Le fichier joint est introuvable.")

    @staticmethod
    def open_url(app):
        """Ouvre le lien internet associé au nœud dans le navigateur par défaut."""
        ws = app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if node.url_link:
                url_str = node.url_link.strip()
                # Sécurité si le protocole a été sauté au moment de la saisie
                if not url_str.startswith(("http://", "https://")):
                    url_str = "https://" + url_str
                QDesktopServices.openUrl(QUrl(url_str))
