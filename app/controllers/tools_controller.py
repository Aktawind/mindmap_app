# controllers/tools_controller.py
import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class ToolsController:

    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    def create_separator(self):
        sep = QWidget()
        sep.setFixedSize(2, 22)
        sep.setStyleSheet("background-color: #cbd5e1; margin: 0 4px;")
        return sep
    
    def auto_center_clicked(self):
        """Méthode appelée lors du clic sur le bouton Auto Center."""
        # On récupère le workspace actif AU MOMENT du clic
        ws = self.current_workspace()
        if ws:
            # S'il y a un workspace ouvert, on lui demande de se centrer
            ws.auto_center_root()