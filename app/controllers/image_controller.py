import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from graphics.items import NodeItem
from services import media_service

class ImageController:
    def __init__(self, app):
        self.app = app

    def attach_image_to_selected(self):
        """Ouvre l'explorateur pour choisir une image, la copie localement et l'affecte au nœud."""
        ws = self.app.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if not nodes:
            QMessageBox.warning(self.app, "Sélection", "Veuillez sélectionner un nœud.")
            return
            
        node = nodes[0] # On applique au premier nœud sélectionné
        
        # Filtre pour n'accepter que des formats d'images courants
        file_path, _ = QFileDialog.getOpenFileName(
            self.app, 
            "Choisir une image pour le nœud", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        
        if not file_path:
            return

        try:
            # Copie dans le dossier .mindmap_attachments de la carte (identique aux fichiers)
            dest_path = media_service.import_image_file(ws, file_path)

            # Mettre à jour le nœud avec le chemin relatif ou absolu stable
            node.image_path = dest_path
            node.image_height = 150 # Hauteur par défaut demandée
            
            if hasattr(node, 'recalculate_size'):
                node.recalculate_size()
            node.update()

            ws.is_dirty = True
            if hasattr(self.app, 'tabs_controller'):
                self.app.tabs_controller.update_title()
            
            self.app.save_state()
            
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur", f"Impossible d'importer l'image :\n{str(e)}")

    def change_image_height(self):
        """Permet de configurer dynamiquement la hauteur de l'image du nœud sélectionné."""
        ws = self.app.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem) and getattr(item, 'image_path', None)]
        
        if not nodes:
            QMessageBox.warning(self.app, "Sélection", "Sélectionnez un nœud contenant une image.")
            return
            
        node = nodes[0]
        current_h = getattr(node, 'image_height', 150)
        
        val, ok = QInputDialog.getInt(
            self.app, "Hauteur de l'image", 
            "Entrez la hauteur en pixels (les proportions seront gardées) :", 
            value=current_h, min=30, max=1000, step=10
        )
        if ok:
            node.image_height = val
            node.recalculate_size()
            node.update()
            self.app.save_state()

    def open_image_full_size(self, node):
        """Ouvre l'image du nœud dans la visionneuse par défaut du système."""
        if getattr(node, 'image_path', None) and os.path.exists(node.image_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(node.image_path))

    def cleanup_orphaned_images(self):
        """Supprime les images du dossier .mindmap_attachments de la carte qui ne sont plus
        utilisées (nœuds image, notes, fond de canevas) ni par les cartes ouvertes, ni par
        leur historique, ni par les autres cartes enregistrées dans le même dossier."""
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None:
            return
        try:
            target_dir = media_service.attachments_dir(ws)
        except OSError:
            return
        media_service.remove_orphans(self.app, target_dir, only_images=True)
