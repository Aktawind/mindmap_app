import os
import shutil
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from graphics.items import NodeItem

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
            # Création du dossier .mindmap_attachments s'il n'existe pas (identique aux fichiers)
            target_dir = os.path.abspath(".mindmap_attachments")
            os.makedirs(target_dir, exist_ok=True)
            
            # Éviter les conflits de nom de fichier
            base_name = os.path.basename(file_path)
            name, ext = os.path.splitext(base_name)
            counter = 1
            new_name = base_name
            while os.path.exists(os.path.join(target_dir, new_name)):
                new_name = f"{name}_{counter}{ext}"
                counter += 1
                
            dest_path = os.path.join(target_dir, new_name)
            shutil.copy(file_path, dest_path)
            
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
        """Supprime les fichiers du dossier .mindmap_attachments qui ne sont plus liés à aucun nœud image."""
        ws = self.app.current_workspace()
        if not ws or not hasattr(ws, 'scene') or ws.scene is None:
            return

        target_dir = os.path.abspath(".mindmap_attachments")
        if not os.path.exists(target_dir):
            return

        # 1. Lister toutes les images actuellement utilisées par les nœuds de la scène
        from graphics.items import NodeItem
        used_images = set()
        if hasattr(self.app, 'tabs'):
            for i in range(self.app.tabs.count()):
                tab_ws = self.app.tabs.widget(i)
                if hasattr(tab_ws, 'scene') and tab_ws.scene:
                    for item in tab_ws.scene.items():
                        if isinstance(item, NodeItem) and getattr(item, 'image_path', None):
                            normalized_path = os.path.abspath(os.path.normpath(item.image_path))
                            used_images.add(normalized_path)

        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        
        try:
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                # 🎯 COMPARAISON SUR LE MÊME FORMAT NORMALISÉ
                abs_file_path = os.path.abspath(os.path.normpath(file_path))
                
                if os.path.isfile(file_path) and filename.lower().endswith(valid_extensions):
                    if abs_file_path not in used_images:
                        os.remove(file_path)
        except Exception as e:
            print(f"Erreur lors du nettoyage des images orphelines : {e}")