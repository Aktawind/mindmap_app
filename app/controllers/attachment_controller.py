import os
import shutil
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from graphics.items import NodeItem
from ui.selection_manager import on_selection_changed

class AttachmentController:
    def __init__(self, app):
        self.app = app

    def get_attachments_dir(self):
        """Retourne le chemin du dossier d'onglets pour le workspace actuel et le crée si nécessaire."""
        ws = self.app.current_workspace()
        if not ws or not ws.current_file_path:
            return None
            
        base_dir = os.path.dirname(ws.current_file_path)
        attachments_dir = os.path.join(base_dir, ".mindmap_attachments")
        
        if not os.path.exists(attachments_dir):
            try:
                os.makedirs(attachments_dir, exist_ok=True)
            except Exception as e:
                print(f"Erreur lors de la création du dossier de pièces jointes : {e}")
                return None
        return attachments_dir

    def remove_file_from_attachments(self, relative_path):
        """Supprime le fichier physique du disque si le chemin est valide et sécurisé."""
        ws = self.app.current_workspace()
        if not ws or not ws.current_file_path or not relative_path:
            return
            
        base_dir = os.path.dirname(ws.current_file_path)
        full_path = os.path.abspath(os.path.join(base_dir, relative_path))
        attachments_dir = self.get_attachments_dir()

        # Sécurité stricte : s'assurer que le fichier est bien à l'intérieur du dossier cible (évite le path traversal)
        if attachments_dir and full_path.startswith(os.path.abspath(attachments_dir)):
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier : {e}")

    def copy_file_to_attachments(self, node_id, source_path):
        """Copie un fichier externe dans le dossier des pièces jointes."""
        attachments_dir = self.get_attachments_dir()
        if not attachments_dir or not source_path or not os.path.exists(source_path):
            return source_path  # Si pas encore sauvegardé, on garde le lien temporaire

        _, ext = os.path.splitext(source_path)
        dest_filename = f"file_{node_id}{ext}"
        dest_path = os.path.join(attachments_dir, dest_filename)

        try:
            shutil.copy2(source_path, dest_path)
            return os.path.join(".mindmap_attachments", dest_filename)
        except Exception as e:
            print(f"Erreur lors de la copie du fichier : {e}")
            return source_path

    def _update_node_ui(self, node):
        """Méthode utilitaire privée pour centraliser la mise à jour visuelle d'un nœud."""
        node.recalculate_size()
        on_selection_changed(self.app)
        node.update()
        self.app.save_state()

    def attach_file(self):
        """Associe un fichier local au nœud sélectionné."""
        ws = self.app.current_workspace()
        if not ws: 
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if not ws.current_file_path:
                QMessageBox.information(
                    self.app, 
                    "Sauvegarde requise", 
                    "Veuillez d'abord enregistrer votre Mind Map (Fichier -> Enregistrer) afin de pouvoir y attacher des fichiers."
                )
                
                # Sécurité dynamique : on cherche si une méthode de sauvegarde existe sous un autre nom
                if hasattr(self.app, 'save_file'):
                    self.app.save_file()
                elif hasattr(self.app, 'save_project'):
                    self.app.save_project()
                elif hasattr(self.app, 'export_controller') and hasattr(self.app.export_controller, 'save'):
                    self.app.export_controller.save()
                else:
                    # Si l'application n'a pas de déclencheur automatique, on laisse l'utilisateur le faire manuellement
                    return

                # Si après tentative c'est toujours vide, on stoppe
                if not ws.current_file_path: 
                    return
                
            path, _ = QFileDialog.getOpenFileName(self.app, "Choisir un document à joindre")
            if path:
                if node.file_path:
                    self.remove_file_from_attachments(node.file_path)
                
                relative_dest = self.copy_file_to_attachments(node.node_id, path)
                node.file_path = relative_dest
                self._update_node_ui(node)

    def attach_url(self):
        """Associe un lien internet au nœud sélectionné."""
        ws = self.app.current_workspace()
        if not ws: 
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            url, ok = QInputDialog.getText(self.app, "Associer une URL", "Entrez l'adresse internet :", 
                                           text=node.url_link or "https://")
            if ok and url.strip():
                node.url_link = url.strip()
                self._update_node_ui(node)

    def detach_links(self):
        """Supprime tous les liens (fichiers et URLs) rattachés au nœud sélectionné."""
        ws = self.app.current_workspace()
        if not ws: 
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]

            if not node.file_path and not node.url_link:
                return

            if node.file_path:
                self.remove_file_from_attachments(node.file_path)
                node.file_path = None

            node.url_link = None
            self._update_node_ui(node)

    def open_file(self):
        """Ouvre le fichier joint ou bascule sur l'URL si aucun fichier n'est configuré."""
        ws = self.app.current_workspace()
        if not ws: 
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            
            # Correction de la faille de récursivité brisée : appel correct de la méthode interne open_url
            if not node.file_path and node.url_link:
                self.open_url()
                return

            if not node.file_path:
                return

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
        """Ouvre le lien internet associé au nœud dans le navigateur par défaut de manière sécurisée."""
        ws = self.app.current_workspace()
        if not ws: 
            return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if node.url_link:
                url_str = node.url_link.strip()
                if not url_str.startswith(("http://", "https://")):
                    url_str = "https://" + url_str
                # Utilisation de fromUserInput pour assainir et encoder proprement l'URL
                QDesktopServices.openUrl(QUrl.fromUserInput(url_str))