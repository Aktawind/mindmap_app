# main.py
import sys
import os
import json
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsPathItem, QFileDialog, 
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QComboBox, QTextEdit, QTabWidget, QInputDialog
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QFontMetrics, 
    QKeySequence, QDesktopServices, QPixmap, QShortcut, QPainterPathStroker, QIcon, QCloseEvent, QPolygonF, QPageLayout, QPageSize
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QObject, QUrl, QSettings, QTimer, QPointF, QMarginsF
from PyQt6.QtPrintSupport import QPrinter



from graphics.items import NodeItem, EdgeItem
from signals import GraphicsSignals
from graphics.scene import MindMapWorkspace

from graphics.items import BRANCH_PALETTES

from ui.menus import create_menus
from ui.toolbar import create_toolbar
from ui.shortcuts import setup_app_shortcuts
from ui.about_dialog import show_app_about_dialog
from ui.node_toolbar import create_node_toolbar

from services.serializer import MindMapSerializer
from services.history_service import HistoryService
from services.project_service import ProjectService

from controllers.graph_controller import GraphController
from controllers.style_controller import StyleController
from controllers.attachment_controller import AttachmentController
from controllers.export_controller import ExportController
from controllers.workspace_controller import WorkspaceController
from controllers.tools_controller import ToolsController

APP_VERSION  = "1.0.7"

class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mindy {APP_VERSION }")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        self._clipboard_node = None

        self.current_workspace_path = None
        self.workspace_files = []

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.graph_controller = GraphController(self)
        self.style_controller = StyleController(self)
        self.attachment_controller = AttachmentController(self)
        self.export_controller = ExportController(self)
        self.workspace_controller = WorkspaceController(self)
        self.tools_controller = ToolsController(self)

        self.project_service = ProjectService(self)
        self.history_service = HistoryService(self)
        self.serializer = MindMapSerializer(self)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        self.load_last_project_on_startup()
      
        last_workspace = self.settings.value("last_collection_path", "")
        
        if last_workspace and os.path.exists(last_workspace):
            QTimer.singleShot(100, lambda: self.load_workspace(last_workspace))
        else:
            self.project_service.new_project()

    def current_workspace(self) -> MindMapWorkspace:
        return self.tabs.currentWidget()
   
    def setup_ui(self):
        self.setCentralWidget(self.tabs)

        create_menus(self)
        create_toolbar(self)
        create_node_toolbar(self)

    def update_routing_button_ui(self):
        if self.btn_toggle_routing.isChecked():
            self.btn_toggle_routing.setText("Liens courbes")
        else:
            self.btn_toggle_routing.setText("Liens droits")

    def toggle_line_routing(self, checked):
        """Bascule le mode de routage des lignes en fonction de l'état du bouton."""
        ws = self.tabs.currentWidget()
        if ws and hasattr(ws, 'scene'):
            # Si coché -> 'curved' (courbe), sinon -> 'orthogonal' (lignes droites/perpendiculaires)
            ws.scene.line_routing_mode = 'curved' if checked else 'orthogonal'
            
            # Met à jour le texte et le helper du bouton
            self.update_routing_button_ui()
            
            # Force chaque ligne à recalculer son tracé
            from graphics.items import EdgeItem
            for item in ws.scene.items():
                if isinstance(item, EdgeItem):
                    item.update_position()
            
            # Rafraîchit l'affichage de la scène
            ws.scene.update()

    def setup_shortcuts(self):
        setup_app_shortcuts(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reposition_style_bar()
        self.overlay.raise_()

    def reposition_style_bar(self):
        self.style_bar.adjustSize()
        x = (self.width() - self.style_bar.width()) // 2
        y = self.height() - self.style_bar.height() - 30
        self.style_bar.move(x, y)

    def toggle_snap_to_grid(self, checked):
        ws = self.current_workspace()
        if not ws: return
        ws.scene.snap_to_grid = checked
        if checked:
            for item in ws.scene.items():
                if isinstance(item, NodeItem):
                    x = round(item.pos().x() / 20) * 20
                    y = round(item.pos().y() / 20) * 20
                    item.setPos(x, y)
            ws.scene.update()
            self.save_state()

    def load_last_project_on_startup(self):
        last_path = self.settings.value("last_project_path", "")
        if last_path and os.path.exists(last_path):
            self.load_project_from_path(last_path)
        else:
            self.new_project(force_empty=True)
            
        QTimer.singleShot(100, self.center_on_graph)

    def center_on_graph(self):
        ws = self.current_workspace()
        if not ws: return
        rect = ws.scene.itemsBoundingRect()
        if not rect.isEmpty():
            ws.view.centerOn(rect.center())

    def close_tab(self, index) -> bool:
        ws = self.tabs.widget(index)
        if ws and ws.is_dirty:
            self.tabs.setCurrentWidget(ws)
            name = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
            reply = QMessageBox.question(
                self, 
                "Modifications non enregistrées",
                f"Le projet '{name}' a été modifié.\nVoulez-vous enregistrer les modifications avant de fermer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_project()
                if ws.is_dirty: return False
            elif reply == QMessageBox.StandardButton.Cancel:
                return False

        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.new_project(force_empty=True)
            self.tabs.removeTab(0)
        return True

    def closeEvent(self, event):
        """Gère la fermeture de l'application et force la sauvegarde des onglets non enregistrés."""
        # On boucle sur tous les onglets pour vérifier s'il y a des modifications en cours
        for i in range(self.tabs.count()):
            ws = self.tabs.widget(i)
            
            # Si l'onglet a été modifié (is_dirty)
            if hasattr(ws, 'is_dirty') and ws.is_dirty:
                # On active l'onglet visuellement pour que l'utilisateur voie ce qu'il sauvegarde
                self.tabs.setCurrentIndex(i)
                
                name = ws.current_file_path if ws.current_file_path else f"Sans titre {i+1}"
                reply = QMessageBox.question(
                    self, 
                    'Enregistrer les modifications',
                    f"Le document '{os.path.basename(name)}' a été modifié.\nVoulez-vous enregistrer les modifications ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # --- CRUCIAL : On force la sauvegarde immédiate ---
                    # On appelle ta méthode de sauvegarde (ajuste le nom si elle s'appelle autrement, ex: self.save_file)
                    saved = self.save_project() 
                    
                    # Si la sauvegarde a été annulée par l'utilisateur dans le prompt de fichier, on stoppe la fermeture
                    if not saved:
                        event.ignore()
                        return
                        
                elif reply == QMessageBox.StandardButton.Cancel:
                    # L'utilisateur a cliqué sur Annuler : on stoppe complètement la fermeture
                    event.ignore()
                    return

        # Si tout est sauvegardé ou que l'utilisateur a dit "Non", on accepte la fermeture
        event.accept()

    def on_tab_changed(self, index):
        self.update_title()
        ws = self.current_workspace()
        if ws:
            is_curved = (ws.scene.line_routing_mode == 'curved')
            self.btn_toggle_routing.blockSignals(True)
            self.btn_toggle_routing.setChecked(is_curved)
            self.btn_toggle_routing.blockSignals(False)
            self.update_routing_button_ui()

            self.btn_snap.blockSignals(True)
            self.btn_snap.setChecked(getattr(ws.scene, 'snap_to_grid', False))
            self.btn_snap.blockSignals(False)
        self.on_selection_changed()
        self.update_workspace_ui()

    def update_title(self):
        ws = self.current_workspace()
        if not ws: return
        base_title = os.path.basename(ws.current_file_path) if ws.current_file_path else "[Nouveau Projet]"
        suffix = " *" if ws.is_dirty else ""
        display_title = base_title + suffix
        self.tabs.setTabText(self.tabs.currentIndex(), display_title)
        
        # Ajout du nom de l'espace de travail dans le titre de la fenêtre si présente
        if self.current_workspace_path:
            workspace_name = os.path.basename(self.current_workspace_path)
            self.setWindowTitle(f"Mindy [{workspace_name}] - {display_title}")
        else:
            self.setWindowTitle(f"Mindy - {display_title}")

    def change_global_routing(self, index):
        ws = self.current_workspace()
        if not ws: return
        mode = self.routing_combo.itemData(index)
        ws.scene.line_routing_mode = mode
        
        for item in ws.scene.items():
            if isinstance(item, EdgeItem):
                item.update_position()
        ws.scene.update()
        self.save_state()

    

    



    def save_state(self):
        """Enregistre l'état actuel de l'espace de travail pour l'historique."""
        ws = self.current_workspace()
        if not ws:
            return
        current_state = self.get_state()
        self.history_service.save_state(ws, current_state)
        
        # On s'assure que l'étoile se met à jour dès qu'un état est enregistré
        self.update_title()

    def undo(self):
        """Annule la dernière action."""
        ws = self.current_workspace()
        if not ws:
            return
        previous_state = self.history_service.undo(ws)
        if previous_state:
            self.apply_state(previous_state)

    def redo(self):
        """Rétablit la dernière action annulée."""
        ws = self.current_workspace()
        if not ws:
            return
        next_state = self.history_service.redo(ws)
        if next_state:
            self.apply_state(next_state)

    def get_state(self):
        return self.serializer.get_state()
    
    def apply_state(self, state_str):
        self.serializer.apply_state(state_str)
    
    def sync_workspace_ui(self, ui_state):
        if not ui_state:
            return

        self.btn_snap.blockSignals(True)
        self.btn_snap.setChecked(
            ui_state["snap_to_grid"]
        )
        self.btn_snap.blockSignals(False)

        is_curved = (
            ui_state["line_routing_mode"]
            == "curved"
        )

        self.btn_toggle_routing.blockSignals(True)
        self.btn_toggle_routing.setChecked(is_curved)
        self.btn_toggle_routing.blockSignals(False)

        self.on_selection_changed()

    

    def copy_selected(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            src = sel[0]
            self._clipboard_node = {
                "label": src.label,
                "shape": src.shape_type,
                "bg": src.bg_color.name(),
                "border": src.border_color.name(),
                "font_color": src.font_color.name(),
                "is_bold": src.is_bold,
                "status": src.status,
                "notes": getattr(src, 'notes', ''),
                "file_path": src.file_path,
                "url_link": src.url_link
            }

    def paste_node(self):
        ws = self.current_workspace()
        if not ws or not self._clipboard_node: return
        
        data = self._clipboard_node
        new_id = f"node_paste_{len(ws.scene.items())}"
        
        center = ws.view.mapToScene(ws.view.viewport().rect().center())
        x, y = center.x(), center.y()
        
        if getattr(ws.scene, 'snap_to_grid', False):
            x = round(x / 20) * 20
            y = round(y / 20) * 20

        new_node = NodeItem(
            new_id, data["label"], x, y,
            shape=data["shape"], bg=data["bg"], border=data["border"], font_color=data["font_color"]
        )
        new_node.is_bold = data["is_bold"]
        new_node.status = data["status"]
        if hasattr(new_node, 'notes'): new_node.notes = data["notes"]
        new_node.file_path = data["file_path"]
        new_node.url_link = data["url_link"]
        
        new_node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        
        ws.scene.addItem(new_node)
        self.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)

    def on_selection_changed(self):
        ws = self.current_workspace()
        if not ws: 
            self.style_bar.hide()
            return
            
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        if len(sel) >= 1:
            self.style_bar.show()
            self.connect_controls.hide()
            if isinstance(sel[0], NodeItem):
                self.node_controls.show()
                self.edge_controls.hide()
                has_links = bool(sel[0].file_path or sel[0].url_link)
                self.btn_open.setVisible(has_links)
                self.btn_detach.setVisible(has_links)
                
                self.shape_combo.blockSignals(True)
                self.shape_combo.setCurrentIndex(self.shape_combo.findData(sel[0].shape_type))
                self.shape_combo.blockSignals(False)
                
                self.status_combo.blockSignals(True)
                self.status_combo.setCurrentIndex(self.status_combo.findData(sel[0].status))
                self.status_combo.blockSignals(False)
                
            elif isinstance(sel[0], EdgeItem):
                self.node_controls.hide()
                self.edge_controls.show()
                
                self.arrow_combo.blockSignals(True)
                self.arrow_combo.setCurrentIndex(self.arrow_combo.findData(sel[0].arrow_dir))
                self.arrow_combo.blockSignals(False)
            self.reposition_style_bar()
        elif len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            self.style_bar.show()
            self.node_controls.hide()
            self.edge_controls.hide()
            self.connect_controls.show()
            self.reposition_style_bar()
        else:
            self.style_bar.hide()

    def on_shape_combo_changed(self, text):
        """Délègue le changement de forme géométrique au StyleController."""
        StyleController.on_shape_combo_changed(self, text)

    def on_status_combo_changed(self, text):
        """Délègue le changement de statut au StyleController."""
        StyleController.on_status_combo_changed(self, text)

    def on_arrow_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            sel[0].arrow_dir = self.arrow_combo.itemData(index)
            sel[0].update()
            self.save_state()

    def on_bg_double_clicked(self, pos):
        ws = self.current_workspace()
        if not ws: return
        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        x, y = pos.x(), pos.y()
        if getattr(ws.scene, 'snap_to_grid', False):
            x = round(x / 20) * 20
            y = round(y / 20) * 20

        if not nodes:
            node = NodeItem('root', "Nouvelle idée centrale", x, y, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        else:
            # Génération d'un ID unique basé sur le temps en millisecondes
            import time
            unique_id = f"node_{int(time.time() * 1000)}"
            node = NodeItem(unique_id, "Nouvelle idée", x, y, bg='#FFF3E0', border='#FFB74D', font_color='#333333')
            
        node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        ws.scene.addItem(node)
        self.save_state()

    def edit_selected_edge(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], EdgeItem):
            self.start_inline_editing(sel[0])

    def start_inline_editing(self, item):
        ws = self.current_workspace()
        if not ws: return
        self.edit_item = item
        self.editor = QTextEdit(ws.view)
        
        if isinstance(item, NodeItem):
            clean_text = item.label.replace('🚨 ', '').replace('⏳ ', '').replace('✅ ', '')
            view_pos = ws.view.mapFromScene(item.pos())
            w = int(item.rect.width())
            h = max(int(item.rect.height()), 40)
            self.editor.setGeometry(view_pos.x() - w//2, view_pos.y() - h//2, w, h)
        else:
            clean_text = item.label
            center = item.path().pointAtPercent(0.5)
            view_pos = ws.view.mapFromScene(center)
            self.editor.setGeometry(view_pos.x() - 75, view_pos.y() - 15, 150, 40)

        self.editor.setText(clean_text)
        self.editor.setStyleSheet("border: 2px solid #60A5FA; background: white; font-family: Segoe UI; font-size: 11pt;")
        self.editor.selectAll()
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        self.editor.show()
        self.editor.setFocus()
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == getattr(self, 'editor', None):
            if event.type() == event.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.commit_edit()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.editor.deleteLater()
                    self.editor = None
                    return True
            elif event.type() == event.Type.FocusOut:
                self.commit_edit()
                return True
        return super().eventFilter(obj, event)

    def commit_edit(self):
        if not hasattr(self, 'editor') or self.editor is None: return
        new_text = self.editor.toPlainText().strip()
        changed = False
        
        if isinstance(self.edit_item, NodeItem):
            if new_text and self.edit_item.label != new_text:
                self.edit_item.label = new_text
                self.edit_item.recalculate_size()
                self.edit_item.update_edges()
                changed = True
        else:
            if self.edit_item.label != new_text:
                self.edit_item.label = new_text
                self.edit_item.update()
                changed = True
            
        self.editor.deleteLater()
        self.editor = None
        if changed:
            self.save_state()

    def on_tab_pressed(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            self.add_child_node(sel[0])

    #-------------------- Gestion des nœuds et liens -------------------- #
    def add_child_node(self, parent_node):
        self.graph_controller.add_child_node(parent_node)
        self.update_title()

    def delete_selected(self):
        self.graph_controller.delete_selected()
        self.update_title()

    def connect_selected_nodes(self):
        self.graph_controller.connect_selected_nodes()
        self.update_title()

    #-------------------- Gestion du style -------------------- #
    def change_color(self, bg_color, border_color):
        self.style_controller.change_color(self, bg_color, border_color)

    def toggle_bold(self):
        self.style_controller.toggle_bold(self)

    #-------------------- Gestion des fichiers et liens -------------------- #
    def attach_file(self):
        self.attachment_controller.attach_file()

    def attach_url(self):
        self.attachment_controller.attach_url()

    def detach_links(self):
        self.attachment_controller.detach_links()

    def open_file(self):
        self.attachment_controller.open_file()

    # -------------------- Gestion de l'espace de travail -------------------- #
    def update_workspace_ui(self):
        self.workspace_controller.update_workspace_ui()

    def auto_save_workspace(self):
        self.workspace_controller.auto_save_workspace()

    def new_workspace(self):
        self.workspace_controller.new_workspace()

    def load_workspace(self, path=None):
        self.workspace_controller.load_workspace(path)

    def add_current_tab_to_workspace(self):
        self.workspace_controller.add_current_tab_to_workspace()

    def remove_current_tab_from_workspace(self):
        self.workspace_controller.remove_current_tab_from_workspace()

    # -------------------- Gestion des projets -------------------- #
    def new_project(self, force_empty=False):
        self.project_service.new_project(force_empty)

    def load_project(self):
        self.project_service.load_project()

    def load_project_from_path(self, path):
        self.project_service.load_project_from_path( path)

    def save_project(self, force_save_as=False):
        self.project_service.save_project(force_save_as)

    def show_about_dialog(self):
        show_app_about_dialog(self, APP_VERSION)
        
    # -------------------- Gestion des exports -------------------- #
    def export_png(self):
        self.export_controller.export_png()

    def export_pdf(self):
        self.export_controller.export_pdf()

    def export_md(self):
        self.export_controller.export_md()

    def auto_center_clicked(self):
        """Méthode appelée lors du clic sur le bouton Auto Center."""
        ws = self.current_workspace()
        if ws:
            # S'il y a un workspace ouvert, on lui demande de se centrer
            if hasattr(ws, 'auto_center_root'):
                ws.auto_center_root()
            elif hasattr(self, 'center_on_graph'):
                self.center_on_graph()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    # Forcer la mise à jour géométrique initiale de la barre de boutons dès l'affichage
    QTimer.singleShot(50, window.reposition_style_bar)
    sys.exit(app.exec())