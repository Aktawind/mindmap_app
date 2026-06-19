# controllers/tools_controller.py
import json
import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget
from graphics.items import NodeItem

class GridController:
    def __init__(self, app):
        self.app = app

    def toggle_snap_to_grid(self, checked):
        ws = self.app.current_workspace()
        ws.scene.snap_to_grid = checked
        if checked:
            for item in ws.scene.items():
                if isinstance(item, NodeItem):
                    x = round(item.pos().x() / 20) * 20
                    y = round(item.pos().y() / 20) * 20
                    item.setPos(x, y)
            ws.scene.update()
            self.app.save_state()