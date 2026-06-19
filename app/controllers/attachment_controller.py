# controllers/attachment_controller.py
import os
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from graphics.items import NodeItem

class AttachmentController:
    def __init__(self, app):
        self.app = app

    def get_attachments_dir(self):
        ws = self.app.current_workspace()
        """Retourne le chemin du dossier d'onglets pour le workspace actuel."""
        if not ws or not ws.current_file_path:
            return None
        # Le dossier .mindmap_attachments est créé à côté du fichier .json
        base_dir = os.path.dirname(ws.current_file_path)
        attachments_dir = os.path.join(base_dir, ".mindmap_attachments")
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)
        return attachments_dir

    def remove_file_from_attachments(self, relative_path):
        ws = self.app.current_workspace()
        """Supprime le fichier physique du disque si le chemin est valide."""
        if not ws or not ws.current_file_path or not relative_path:
            return
        base_dir = os.path.dirname(ws.current_file_path)
        full_path = os.path.abspath(os.path.join(base_dir, relative_path))
        
        # Sécurité : on vérifie que le fichier est bien dans notre dossier cible avant de delete
        if ".mindmap_attachments" in full_path and os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier : {e}")

    def copy_file_to_attachments(self, node_id, source_path):
        ws = self.app.current_workspace()
        """Copie un fichier externe dans le dossier des pièces jointes."""
        attachments_dir = self.get_attachments_dir()
        if not attachments_dir or not source_path or not os.path.exists(source_path):
            return source_path # Si pas encore sauvegardé, on garde le lien temporaire

        # On extrait l'extension (.pdf, .docx, etc.)
        _, ext = os.path.splitext(source_path)
        # On crée un nom unique basé sur l'id du nœud pour éviter les conflits
        dest_filename = f"file_{node_id}{ext}"
        dest_path = os.path.join(attachments_dir, dest_filename)

        try:
            import shutil
            shutil.copy2(source_path, dest_path)
            return os.path.join(".mindmap_attachments", dest_filename)
        except Exception as e:
            print(f"Erreur lors de la copie du fichier : {e}")
            return source_path

    def attach_file(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if not ws.current_file_path:
                QMessageBox.information(self.app, "Sauvegarde requise", "Veuillez d'abord enregistrer votre Mind Map afin de pouvoir y attacher des fichiers.")
                self.app.save_file()
                if not ws.current_file_path: return # Annulé par l'utilisateur
                
            path, _ = QFileDialog.getOpenFileName(self.app, "Choisir un document à joindre")
            if path:
                if node.file_path:
                    self.remove_file_from_attachments(node.file_path)
                
                # Copie et récupération du chemin relatif
                relative_dest = self.copy_file_to_attachments(node.node_id, path)
                node.file_path = relative_dest
                node.recalculate_size()
                self.app.on_selection_changed()
                node.update()
                self.app.save_state()

    def attach_url(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            url, ok = QInputDialog.getText(self.app, "Associer une URL", "Entrez l'adresse internet :", text=node.url_link or "https://")
            if ok and url.strip():
                node.url_link = url.strip()
                node.recalculate_size()
                self.app.on_selection_changed()
                node.update()
                self.app.save_state()

    def detach_links(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]

            # Si le nœud n'a ni fichier ni URL, rien à faire
            if not node.file_path and not node.url_link:
                return

            # 1. Gestion du fichier s'il existe
            if node.file_path:
                # Suppression physique du fichier dans .mindmap_attachments
                self.remove_file_from_attachments(node.file_path)
                node.file_path = None

            # 2. Gestion de l'URL (s'exécute TOUJOURS, même s'il n'y a pas de fichier)
            node.url_link = None
            
            # 3. Rafraîchissement visuel et sauvegarde de l'état
            node.recalculate_size()
            self.app.on_selection_changed()
            node.update()
            self.app.save_state()

    def open_file(self):
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            
            # SÉCURITÉ : Si le nœud a une URL mais pas de fichier local,
            # on bascule automatiquement sur l'ouverture de l'URL !
            if not node.file_path and node.url_link:
                self.app.open_url(self.app)
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
                QMessageBox.warning(self.app, "Erreur", "Le fichier joint est introuvable.")

    def open_url(self):
        """Ouvre le lien internet associé au nœud dans le navigateur par défaut."""
        ws = self.app.current_workspace()
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
