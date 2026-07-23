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
        """Retourne le chemin du dossier des pièces jointes pour le workspace actuel."""
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

        if attachments_dir and full_path.startswith(os.path.abspath(attachments_dir)):
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier : {e}")

    def copy_file_to_attachments(self, node_id, source_path, attachment_index):
        """Copie un fichier externe dans le dossier des pièces jointes avec un index unique."""
        attachments_dir = self.get_attachments_dir()
        if not attachments_dir or not source_path or not os.path.exists(source_path):
            return source_path

        _, ext = os.path.splitext(source_path)
        dest_filename = f"file_{node_id}_{attachment_index}{ext}"
        dest_path = os.path.join(attachments_dir, dest_filename)

        try:
            shutil.copy2(source_path, dest_path)
            return os.path.join(".mindmap_attachments", dest_filename)
        except Exception as e:
            print(f"Erreur lors de la copie du fichier : {e}")
            return source_path

    def _ensure_attachments_layout(self, node):
        """S'assure que la liste d'attachements est initialisée et migre les anciens attributs."""
        if not hasattr(node, 'attachments') or node.attachments is None:
            node.attachments = []
            
        # Rétrocompatibilité : migration d'une ancienne URL unique si présente
        if getattr(node, 'url_link', None):
            node.attachments.append({
                "name": f"🔗 {node.url_link}",
                "path": node.url_link,
                "type": "url",
                "is_local_copy": False
            })
            node.url_link = None

    def _update_node_ui(self, node):
        """Méthode utilitaire privée pour centraliser la mise à jour visuelle d'un nœud."""
        ws = self.app.current_workspace()
        if ws:
            ws.is_dirty = True
        node.recalculate_size()
        if hasattr(node, 'edges'):
            for edge in node.edges:
                if hasattr(edge, 'update_position'):
                    edge.update_position()
        on_selection_changed(self.app)
        node.update()
        self.app.save_state()

    def attach_file(self):
        """Associe un ou plusieurs fichiers au nœud sélectionné."""
        ws = self.app.current_workspace()
        if not ws: return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            self._ensure_attachments_layout(node)

            if not ws.current_file_path:
                QMessageBox.information(self.app, "Sauvegarde requise", 
                                        "Veuillez d'abord enregistrer votre Mind Map afin de pouvoir y attacher des fichiers.")
                if hasattr(self.app, 'save_project'): self.app.save_project()
                if not ws.current_file_path: return
                
            paths, _ = QFileDialog.getOpenFileNames(self.app, "Choisir un ou plusieurs documents à joindre")
            if paths:
                for path in paths:
                    original_name = os.path.basename(path)
                    
                    msg_box = QMessageBox(self.app)
                    msg_box.setWindowTitle("Méthode d'intégration")
                    msg_box.setText(f"Comment souhaitez-vous joindre le fichier :\n'{original_name}' ?")
                    btn_copy = msg_box.addButton("Créer une copie locale", QMessageBox.ButtonRole.AcceptRole)
                    btn_link = msg_box.addButton("Lien direct", QMessageBox.ButtonRole.AcceptRole)
                    msg_box.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
                    msg_box.exec()
                    
                    if msg_box.clickedButton() == btn_copy:
                        idx = len(node.attachments)
                        relative_dest = self.copy_file_to_attachments(node.node_id, path, idx)
                        node.attachments.append({
                            "name": original_name,
                            "path": relative_dest,
                            "type": "file",
                            "is_local_copy": True
                        })
                    elif msg_box.clickedButton() == btn_link:
                        node.attachments.append({
                            "name": original_name,
                            "path": path,
                            "type": "file",
                            "is_local_copy": False
                        })
                self._update_node_ui(node)

    def attach_url(self):
        """Associe une nouvelle URL à la liste des pièces jointes du nœud."""
        ws = self.app.current_workspace()
        if not ws: return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            self._ensure_attachments_layout(node)

            url, ok = QInputDialog.getText(self.app, "Ajouter une URL", "Entrez l'adresse internet (URL) :", text="https://")
            if ok and url.strip() and url.strip() != "https://":
                url_str = url.strip()
                # On utilise l'URL ou un nom épuré pour l'affichage sous le label
                display_name = url_str.replace("https://", "").replace("http://", "")
                
                node.attachments.append({
                    "name": f"🔗 {display_name}",
                    "path": url_str,
                    "type": "url",
                    "is_local_copy": False
                })
                self._update_node_ui(node)

    def clean_orphan_attachments(self):
        """Parcourt le dossier des pièces jointes et supprime les fichiers qui ne sont plus associés à aucun nœud."""
        ws = self.app.current_workspace()
        attachments_dir = self.get_attachments_dir()
        
        # S'il n'y a pas de workspace ou que le dossier de pièces jointes n'existe pas, rien à nettoyer
        if not ws or not attachments_dir or not os.path.exists(attachments_dir):
            return

        # 1. Collecter tous les chemins de fichiers relatifs utilisés par tous les nœuds de la scène
        used_paths = set()
        if hasattr(self.app, 'tabs'):
            for i in range(self.app.tabs.count()):
                tab_ws = self.app.tabs.widget(i)
                if hasattr(tab_ws, 'scene') and tab_ws.scene:
                    for item in tab_ws.scene.items():
                        if isinstance(item, NodeItem):
                            attachments = getattr(item, 'attachments', [])
                            for att in attachments:
                                if att.get("type") == "file" and att.get("is_local_copy") and att.get("path"):
                                    used_paths.add(os.path.basename(att["path"]))

        # 2. Lister les fichiers physiques présents dans le dossier .mindmap_attachments
        try:
            for filename in os.listdir(attachments_dir):
                file_path = os.path.join(attachments_dir, filename)
                
                # S'assurer que c'est un fichier et qu'il n'est plus utilisé par aucun nœud
                if os.path.isfile(file_path) and filename not in used_paths:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Impossible de supprimer le fichier orphelin {filename} : {e}")
        except Exception as e:
            print(f"Erreur lors du parcours du dossier d'attachements : {e}")

    def detach_links(self):
        """Affiche la liste complète pour permettre à l'utilisateur d'en supprimer une spécifique."""
        ws = self.app.current_workspace()
        if not ws: return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            self._ensure_attachments_layout(node)

            if not node.attachments:
                return

            items = [att["name"] for att in node.attachments]
            choice, ok = QInputDialog.getItem(self.app, "Supprimer un élément", 
                                              "Sélectionnez l'élément à détacher du nœud :", items, 0, False)
            
            if ok and choice:
                target_att = next((att for att in node.attachments if att["name"] == choice), None)
                if target_att:
                    # 🟢 MODIFICATION : On retire simplement l'appel à self.remove_file_from_attachments(...)
                    # Le fichier physique reste dans le dossier, on l'enlève juste du nœud en mémoire.
                    node.attachments.remove(target_att)
                    self._update_node_ui(node)

    def open_specific_file(self, attachment):
        """Appelé lors du clic direct avec la petite main sur le texte sous le nœud."""
        ws = self.app.current_workspace()
        if not ws or not attachment: return
        self._launch_attachment(ws, attachment)

    def open_file(self):
        """Bouton global de la barre d'outils."""
        ws = self.app.current_workspace()
        if not ws: return
            
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            self._ensure_attachments_layout(node)

            if not node.attachments:
                return

            if len(node.attachments) == 1:
                self._launch_attachment(ws, node.attachments[0])
            else:
                items = [att["name"] for att in node.attachments]
                choice, ok = QInputDialog.getItem(self.app, "Ouvrir un élément", 
                                                  "Sélectionnez l'élément à ouvrir :", items, 0, False)
                if ok and choice:
                    target_att = next((att for att in node.attachments if att["name"] == choice), None)
                    if target_att:
                        self._launch_attachment(ws, target_att)

    def _launch_attachment(self, ws, attachment):
        """Méthode unifiée pour exécuter l'ouverture système d'un fichier ou d'une URL."""
        path = attachment["path"]
        
        if attachment.get("type") == "url":
            url_str = path.strip()
            if not url_str.startswith(("http://", "https://")):
                url_str = "https://" + url_str
            QDesktopServices.openUrl(QUrl.fromUserInput(url_str))
        else:
            # Traitement des fichiers
            if attachment.get("is_local_copy") and not os.path.isabs(path) and ws.current_file_path:
                base_dir = os.path.dirname(ws.current_file_path)
                full_path = os.path.abspath(os.path.join(base_dir, path))
            else:
                full_path = path

            if os.path.exists(full_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
            else:
                QMessageBox.warning(self.app, "Erreur", f"Le fichier '{attachment['name']}' est introuvable.")