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
from ui.shortcuts import setup_app_shortcuts
from ui.about_dialog import show_app_about_dialog

from services.serializer import MindMapSerializer
from services.history_service import HistoryService

APP_VERSION  = "1.0.7"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


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
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        self.load_last_project_on_startup()
      
        last_workspace = self.settings.value("last_collection_path", "")
        
        if last_workspace and os.path.exists(last_workspace):
            # Si un espace existait, on le charge directement (sans créer de projet vierge avant)
            QTimer.singleShot(100, lambda: self.load_workspace(last_workspace))
        else:
            # S'il n'y a aucun historique, ALORS SEULEMENT on ouvre un projet vierge par défaut
            self.new_project()

    def current_workspace(self) -> MindMapWorkspace:
        return self.tabs.currentWidget()

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

    def setup_ui(self):
        self.setCentralWidget(self.tabs)

        self.add_tab_button = QPushButton("➕ Ajouter un onglet")
        self.add_tab_button.clicked.connect(self.new_project)
        self.tabs.setCornerWidget(self.add_tab_button, Qt.Corner.TopRightCorner)

        create_menus(self)

        workspace_toolbar = self.addToolBar("workspace")
        workspace_toolbar.setMovable(False)
        workspace_toolbar.setStyleSheet("""
            QToolBar { background: #F1F5F9; border-bottom: 1px solid #CBD5E1; padding: 4px; spacing: 8px; }
            QPushButton { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QPushButton:hover { background: #E2E8F0; }
            QLabel { font-size: 11px; color: #475569; font-weight: bold; }
        """)

        # Label d'information sur la workspace active
        self.lbl_workspace_status = QLabel("📂 Espace de travail : Aucun")
        workspace_toolbar.addWidget(self.lbl_workspace_status)
        workspace_toolbar.addSeparator()

        btn_add_to_coll = QPushButton("➕")
        btn_add_to_coll.setToolTip("Inclure l'onglet actuel dans l'espace de travail")
        btn_remove_from_coll = QPushButton("❌")
        btn_remove_from_coll.setToolTip("Retirer l'onglet actuel de l'espace de travail")
        workspace_toolbar.addSeparator()
        workspace_toolbar.addWidget(btn_add_to_coll)
        workspace_toolbar.addWidget(btn_remove_from_coll)
        btn_add_to_coll.clicked.connect(self.add_current_tab_to_workspace)
        btn_remove_from_coll.clicked.connect(self.remove_current_tab_from_workspace)

        self.header_right_widget = QWidget()
        hr_layout = QHBoxLayout(self.header_right_widget)
        hr_layout.setContentsMargins(0, 0, 10, 0)

        btn_save = QPushButton("💾")
        btn_save.setToolTip("Sauvegarder")
        btn_save.clicked.connect(self.save_project) 
        workspace_toolbar.addWidget(btn_save)

        self.btn_snap = QPushButton(" 🧲 Aimant Grille ")
        self.btn_snap.setCheckable(True)
        self.btn_snap.setStyleSheet("""
            QPushButton { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #f1f5f9; }
            QPushButton:checked { background: #3B82F6; color: white; border-color: #2563EB; font-weight: bold; }
        """)
        self.btn_snap.clicked.connect(self.toggle_snap_to_grid)
        workspace_toolbar.addWidget(self.btn_snap)

        # Crée le bouton et active le mode "Toggle" (mémorisable)
        self.btn_toggle_routing = QPushButton("Liens courbes")
        self.btn_toggle_routing.setCheckable(True)
        self.btn_toggle_routing.setStyleSheet("""
            QPushButton { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #ffffff; font-weight: bold; }
        """)
        self.btn_toggle_routing.clicked.connect(self.toggle_line_routing)
        workspace_toolbar.addWidget(self.btn_toggle_routing)
        
        self.template_combo = QComboBox()
        self.template_combo.addItem("Choisir un template...")
        self.template_combo.addItem("🎯 Cadrage d'Idée", "cadrage_idee.json")
        self.template_combo.addItem("🔍 Résolution de Problème", "resolution_probleme.json")
        self.template_combo.addItem("⏳ Organisation des priorités", "gestion_temps.json")
        self.template_combo.addItem("🧠 Brain Dump", "brain_dump.json")
        self.template_combo.addItem("🚀 Onboarding Technique", "onboarding_technique.json")
        self.template_combo.addItem("🎨 Hub Multi-Passions", "hub_passions.json")
        self.template_combo.addItem("✈️ Organisation d'un Voyage", "organisation_voyage.json")
        self.template_combo.addItem("🗣️ Préparation Réunion", "preparation_reunion.json")
        self.template_combo.addItem("🏁 Rétrospective de Fin de Projet", "retro_projet.json")
        self.template_combo.addItem("☀️ Daily Capsule", "daily_capsule.json")
        self.template_combo.addItem("🔋 Santé Mentale et Énergie", "sante_mentale_energie.json")
        self.template_combo.addItem("🚨 Urgence Colère", "urgence_colere.json")
        self.template_combo.setStyleSheet("""
            QComboBox { border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 5px; background: white; }
        """)
        self.template_combo.currentIndexChanged.connect(self.apply_template)
        workspace_toolbar.addWidget(self.template_combo)
       
        # 1. Création du bouton Auto Center
        btn_center = QPushButton("Auto Center")
        btn_center.setToolTip("Centrer la vue sur le nœud principal")
        # Optionnel : appliquez un style similaire à vos autres boutons si nécessaire
        btn_center.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; 
                color: white; 
                border-radius: 4px; 
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        btn_center.clicked.connect(self.auto_center_clicked)
        workspace_toolbar.addWidget(btn_center)

        self.style_bar = QFrame(self)
        self.style_bar.setObjectName("StyleBar") # <-- On lui donne un nom unique
        self.style_bar.setStyleSheet("""
            #StyleBar { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }
            #StyleBar QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 12px; }
            #StyleBar QPushButton:hover { background: #e2e8f0; }
            #StyleBar QComboBox { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 4px; border-radius: 8px; min-width: 110px; }
        """)
        style_layout = QHBoxLayout(self.style_bar)
        
        self.node_controls = QWidget()
        nc_layout = QHBoxLayout(self.node_controls)
        nc_layout.setContentsMargins(0,0,0,0)
        
        btn_bold = QPushButton("Bold")
        btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        btn_bold.setFixedSize(38, 26)
        btn_bold.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
        btn_bold.clicked.connect(self.toggle_bold)
        nc_layout.addWidget(btn_bold)
        
        nc_layout.addWidget(self.create_separator())
        
        self.shape_combo = QComboBox()
        self.shape_combo.addItem("Rectangle", "box")
        self.shape_combo.addItem("Losange", "diamond")
        self.shape_combo.addItem("Ellipse", "ellipse")
        self.shape_combo.currentIndexChanged.connect(self.on_shape_combo_changed)
        nc_layout.addWidget(self.shape_combo)
        
        nc_layout.addWidget(self.create_separator())

        self.status_combo = QComboBox()
        self.status_combo.addItem("⚪ Aucun statut", "none")
        self.status_combo.addItem("🚨 Urgent", "urgent")
        self.status_combo.addItem("⏳ En cours", "progress")
        self.status_combo.addItem("✅ Terminé", "done")
        self.status_combo.currentIndexChanged.connect(self.on_status_combo_changed)
        nc_layout.addWidget(self.status_combo)

        nc_layout.addWidget(self.create_separator())
        
        for color, border in [('#60A5FA', '#3B82F6'), ('#E0F7FA', '#4DD0E1'), ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'), ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')]:            
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"background: {color}; border: 2px solid {border}; border-radius: 11px;")
            btn.clicked.connect(lambda checked, c=color, b=border: self.change_color(c, b))
            nc_layout.addWidget(btn)
            
        nc_layout.addWidget(self.create_separator())
        
        btn_attach = QPushButton("📎 Fichier")
        btn_attach.clicked.connect(self.attach_file)
        nc_layout.addWidget(btn_attach)
        
        btn_url = QPushButton("🔗 URL")
        btn_url.clicked.connect(self.attach_url)
        nc_layout.addWidget(btn_url)
        
        self.btn_open = QPushButton("📂 Ouvrir")
        self.btn_open.setStyleSheet("background: #2D3748; color: white;")
        self.btn_open.clicked.connect(self.open_file)
        nc_layout.addWidget(self.btn_open)

        self.btn_detach = QPushButton("❌ Dissocier")
        self.btn_detach.setStyleSheet("background: #FED7D7; color: #C53030;")
        self.btn_detach.clicked.connect(self.detach_links)
        nc_layout.addWidget(self.btn_detach)
        
        style_layout.addWidget(self.node_controls)
        
        self.edge_controls = QWidget()
        ec_layout = QHBoxLayout(self.edge_controls)
        ec_layout.setContentsMargins(0,0,0,0)
        
        btn_edit_edge = QPushButton("Texte de branche")
        btn_edit_edge.clicked.connect(self.edit_selected_edge)
        ec_layout.addWidget(btn_edit_edge)
        
        ec_layout.addWidget(self.create_separator())
        
        self.arrow_combo = QComboBox()
        self.arrow_combo.addItem("➖ Aucune flèche", "none")
        self.arrow_combo.addItem("➡️ Flèche Avant", "forward")
        self.arrow_combo.addItem("⬅️ Flèche Arrière", "backward")
        self.arrow_combo.addItem("↔️ Double flèche", "both")
        self.arrow_combo.currentIndexChanged.connect(self.on_arrow_combo_changed)
        ec_layout.addWidget(self.arrow_combo)
        
        style_layout.addWidget(self.edge_controls)
        
        self.connect_controls = QWidget()
        cc_layout = QHBoxLayout(self.connect_controls)
        cc_layout.setContentsMargins(0,0,0,0)
        btn_connect = QPushButton("Relier les nœuds")
        btn_connect.setStyleSheet("background: #EBF8FF; border: 1px solid #90CDF4; color: #2B6CB0; font-weight: bold;")
        btn_connect.clicked.connect(self.connect_selected_nodes)
        cc_layout.addWidget(btn_connect)
        style_layout.addWidget(self.connect_controls)
        
        self.style_bar.hide()
        
        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background: rgba(255,255,255,0.95); border-radius: 8px; border: 1px solid #ddd;")
        ol_layout = QVBoxLayout(self.overlay)
        lbl = QLabel("<b>Commandes :</b><br>- Double-clic vide : Nouveau nœud<br>- Double-clic : Éditer le texte<br>- Sélect + Tab : Ajouter une branche<br>- Ctrl+C / Ctrl+V : Copier/Coller<br>- Ctrl + Clic : Sélectionner 2 nœuds<br>- Suppr : Supprimer l'élément")
        lbl.setFont(QFont("Segoe UI", 9))
        ol_layout.addWidget(lbl)
        self.overlay.resize(230, 140)
        self.overlay.move(20, 100)

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

    def get_attachments_dir(self, ws):
        """Retourne le chemin du dossier d'onglets pour le workspace actuel."""
        if not ws or not ws.current_file_path:
            return None
        # Le dossier .mindmap_attachments est créé à côté du fichier .json
        base_dir = os.path.dirname(ws.current_file_path)
        attachments_dir = os.path.join(base_dir, ".mindmap_attachments")
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)
        return attachments_dir

    def copy_file_to_attachments(self, ws, node_id, source_path):
        """Copie un fichier externe dans le dossier des pièces jointes."""
        attachments_dir = self.get_attachments_dir(ws)
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
            # IMPORTANT : On stocke un chemin RELATIF dans le JSON.
            # Ainsi, si vous déplacez le projet complet (.json + dossier), les liens fonctionnent toujours !
            return os.path.join(".mindmap_attachments", dest_filename)
        except Exception as e:
            print(f"Erreur lors de la copie du fichier : {e}")
            return source_path

    def remove_file_from_attachments(self, ws, relative_path):
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

    def save_state(self):
        """Enregistre l'état actuel de l'espace de travail pour l'historique."""
        ws = self.current_workspace()
        if not ws:
            return
        current_state = self.get_state()
        HistoryService.save_state(ws, current_state)

    def undo(self):
        """Annule la dernière action."""
        ws = self.current_workspace()
        if not ws:
            return
        previous_state = HistoryService.undo(ws)
        if previous_state:
            self.apply_state(previous_state)

    def redo(self):
        """Rétablit la dernière action annulée."""
        ws = self.current_workspace()
        if not ws:
            return
        next_state = HistoryService.redo(ws)
        if next_state:
            self.apply_state(next_state)

    def get_state(self):
        ws = self.current_workspace()

        if not ws:
            return "{}"

        return MindMapSerializer.get_state(ws)
    
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

    def apply_state(self, state_str):
        ws = self.current_workspace()

        if not ws:
            return

        ui_state = MindMapSerializer.load_into_workspace(
            ws,
            state_str,
            self.start_inline_editing
        )

        self.sync_workspace_ui(ui_state)

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

    def on_shape_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            for node in nodes:
                node.shape_type = self.shape_combo.itemData(index)
                node.update()
                node.recalculate_size()
            self.save_state()

    def on_status_combo_changed(self, index):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]

        if nodes:
            for node in nodes:
                node.label = node.label.replace("🚨 ", "").replace("⏳ ", "").replace("✅ ", "")
                node.status = self.status_combo.itemData(index)
                node.recalculate_size()
                node.update()
            self.save_state()

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

    def delete_selected(self):
        if hasattr(self, 'editor') and self.editor is not None: return
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if not sel: return
        
        for item in sel:
            if isinstance(item, NodeItem):
                if item.file_path:
                    self.remove_file_from_attachments(ws, item.file_path)
                for edge in list(item.edges):
                    if edge in edge.source_node.edges: edge.source_node.edges.remove(edge)
                    if edge in edge.dest_node.edges: edge.dest_node.edges.remove(edge)
                    if edge.scene() == ws.scene: ws.scene.removeItem(edge)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
            elif isinstance(item, EdgeItem):
                if item in item.source_node.edges: item.source_node.edges.remove(item)
                if item in item.dest_node.edges: item.dest_node.edges.remove(item)
                if item.scene() == ws.scene: ws.scene.removeItem(item)
                    
        self.save_state()

    def calculate_smart_position(self, parent_node):
        ws = self.current_workspace()
        if not ws or not parent_node:
            return 150, 0
            
        parent_right_edge = parent_node.pos().x() + (parent_node.rect.width() / 2)
        target_x = parent_right_edge + 150
        
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        if child_edges:
            lowest_y = parent_node.pos().y()
            for e in child_edges:
                if e.dest_node.pos().y() > lowest_y: 
                    lowest_y = e.dest_node.pos().y()
            target_y = lowest_y + 85
        else:
            target_y = parent_node.pos().y()

        overlap = True
        all_nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        
        if len(all_nodes) <= 1:
            return target_x, target_y

        iterations = 0
        while overlap and iterations < 100:
            overlap = False
            iterations += 1
            for n in all_nodes:
                if n == parent_node: 
                    continue
                if abs(n.pos().x() - target_x) < 180 and abs(n.pos().y() - target_y) < 65:
                    target_y += 85
                    overlap = True
                    break
        return target_x, target_y

    def add_child_node(self, parent_node):
        ws = self.current_workspace()
        new_id = f"node_{len(ws.scene.items())}"
        
        t_x, t_y = self.calculate_smart_position(parent_node)
        if getattr(ws.scene, 'snap_to_grid', False):
            t_x = round(t_x / 20) * 20
            t_y = round(t_y / 20) * 20

        bg, border, text_col, edge_col = parent_node.bg_color.name(), parent_node.border_color.name(), parent_node.font_color.name(), '#A0AEC0'
        child_edges = [e for e in parent_node.edges if e.source_node == parent_node]
        
        if parent_node.node_id == 'root':
            pal = BRANCH_PALETTES[len(child_edges) % len(BRANCH_PALETTES)]
            bg, border, text_col, edge_col = pal['bg'], pal['border'], pal['text'], pal['edge']
        else:
            p_edge = next((e for e in parent_node.edges if e.dest_node == parent_node), None)
            if p_edge: edge_col = p_edge.color.name()

        new_node = NodeItem(new_id, "Nouvelle sous-idée", t_x, t_y, shape='box', bg=bg, border=border, font_color=text_col)
        new_node.signals.itemDoubleClicked.connect(self.start_inline_editing)
        
        edge = EdgeItem(f"edge_{len(ws.scene.items())}", parent_node, new_node, "", color=edge_col)
        edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
        
        ws.scene.addItem(new_node)
        ws.scene.addItem(edge)
        self.save_state()
        
        ws.scene.clearSelection()
        new_node.setSelected(True)
        self.start_inline_editing(new_node)

    def connect_selected_nodes(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 2 and isinstance(sel[0], NodeItem) and isinstance(sel[1], NodeItem):
            node1, node2 = sel[0], sel[1]
            already_linked = any(
                (e.source_node == node1 and e.dest_node == node2) or 
                (e.source_node == node2 and e.dest_node == node1) 
                for e in node1.edges
            )
            if not already_linked:
                link_color = node1.border_color
                edge = EdgeItem(f"edge_{len(ws.scene.items())}", node1, node2, "", color=link_color)
                edge.signals.itemDoubleClicked.connect(self.start_inline_editing)
                ws.scene.addItem(edge)
                ws.scene.clearSelection()
                edge.setSelected(True)
                self.save_state()

    def toggle_bold(self):
        ws = self.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            # Règle d'or : si au moins un nœud n'est pas en gras, on applique le gras à tous.
            # Sinon, on désactive le gras pour tous.
            any_not_bold = any(not node.is_bold for node in nodes)
            target_bold = any_not_bold
            
            for node in nodes:
                node.is_bold = target_bold
                node.update()
                
            self.save_state()

    def apply_color_downward(self, node, bg_color, border_color):
        """Applique la couleur au nœud et descend récursivement vers tous ses enfants."""
        if not node:
            return

        # 1. On applique la couleur au nœud actuel
        node.bg_color = QColor(bg_color)
        node.border_color = QColor(border_color)
        node.update()

        # 2. On parcourt toutes les branches connectées à ce nœud
        for edge in node.edges:
            # Sécurité : on vérifie que le nœud actuel est bien la SOURCE du lien
            # (ce qui garantit qu'on descend vers l'enfant, sans remonter vers le parent)
            if edge.source_node == node:
                # Optionnel : Si vous souhaitez aussi recolorer le trait de la branche
                edge.color = QColor(border_color)
                edge.update()
                
                # Appel récursif sur le nœud destination (l'enfant)
                self.apply_color_downward(edge.dest_node, bg_color, border_color)

    def change_color(self, color, border):
        ws = self.current_workspace()
        if not ws: return
        
        sel = ws.scene.selectedItems()
        nodes = [item for item in sel if isinstance(item, NodeItem)]
        
        if nodes:
            # On applique la couleur en cascade à CHAQUE nœud sélectionné
            for node in nodes:
                self.apply_color_downward(node, color, border)
            
            # Un seul snapshot de l'état pour tout le groupe
            self.save_state()

    def apply_color_hierarchy(self, node, bg, border, text_col, edge_col):
        node.bg_color = QColor(bg)
        node.border_color = QColor(border)
        node.font_color = QColor(text_col)
        node.update()
        for edge in node.edges:
            if edge.source_node == node:
                edge.color = QColor(edge_col)
                edge.update()
                self.apply_color_hierarchy(edge.dest_node, bg, border, text_col, edge_col)

    def attach_file(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            if not ws.current_file_path:
                QMessageBox.information(self, "Sauvegarde requise", "Veuillez d'abord enregistrer votre Mind Map afin de pouvoir y attacher des fichiers.")
                self.save_file()
                if not ws.current_file_path: return # Annulé par l'utilisateur
                
            path, _ = QFileDialog.getOpenFileName(self, "Choisir un document à joindre")
            if path:
                if node.file_path:
                    self.remove_file_from_attachments(ws, node.file_path)
                
                # Copie et récupération du chemin relatif
                relative_dest = self.copy_file_to_attachments(ws, node.node_id, path)
                node.file_path = relative_dest
                node.recalculate_size()
                self.on_selection_changed()
                node.update()
                self.save_state()

    def attach_url(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            url, ok = QInputDialog.getText(self, "Associer une URL", "Entrez l'adresse internet :", text=node.url_link or "https://")
            if ok and url.strip():
                node.url_link = url.strip()
                node.recalculate_size()
                self.on_selection_changed()
                node.update()
                self.save_state()

    def detach_links(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]

            if node.file_path:
                # Suppression physique du fichier dans .mindmap_attachments
                self.remove_file_from_attachments(ws, node.file_path)
                node.file_path = None
                node.url_link = None
                node.recalculate_size()
                self.on_selection_changed()
                node.update()
                self.save_state()


    def update_workspace_ui(self):
        """ Met à jour le texte de la barre d'outils pour afficher la workspace active """
        if self.current_workspace_path:
            name = os.path.basename(self.current_workspace_path)
            count = len(self.workspace_files)
            self.lbl_workspace_status.setText(f"📁 Workspace :  {name} ({count} carte{'s' if count > 1 else ''})")
        else:
            self.lbl_workspace_status.setText("📁 Workspace : Aucun")

    def auto_save_workspace(self):
        """ Écrit instantanément les modifications dans le fichier .mindy """
        if not self.current_workspace_path:
            return
        
        data = {
            "version": "1.0",
            "files": self.workspace_files
        }
        try:
            with open(self.current_workspace_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.update_workspace_ui()
        except Exception as e:
            QMessageBox.critical(self, "Erreur Sauvegarde", f"Impossible de mettre à jour la workspace :\n{str(e)}")

    def new_workspace(self):
        """ Crée un nouveau fichier de workspace vide et nettoie l'espace """
        path, _ = QFileDialog.getSaveFileName(self, "Créer une nouvelle workspace", "MaSessionDuMatin.mindy", "workspace Mindy (*.mindy)")
        if not path:
            return

        self.current_workspace_path = path
        self.workspace_files = []

        # Nettoyage propre des onglets actuels
        self.tabs.blockSignals(True)
        try:
            self.tabs.clear()
        finally:
            self.tabs.blockSignals(False)

        self.new_project() # Ouvre un premier onglet vierge
        self.auto_save_workspace()
        self.update_title()

    def load_workspace(self, path=None):
        """ Charge une workspace (soit via explorateur si path=None, soit directement au démarrage) """
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un Espace de travail", "", "Espace Mindy (*.mindy)")
            if not path:
                return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_paths = data.get("files", [])

            # Bloquer les signaux pour vider proprement les onglets actuels
            self.tabs.blockSignals(True)
            try:
                self.tabs.clear()
            finally:
                self.tabs.blockSignals(False)

            self.current_workspace_path = path
            self.workspace_files = []

            # Charger uniquement les fichiers JSON valides sur le disque
            for f_path in file_paths:
                if os.path.exists(f_path):
                    self.load_project_from_path(f_path)
                    self.workspace_files.append(f_path)

            # Si le fichier .mindy était vide, on crée un onglet vierge par défaut
            if not self.workspace_files:
                self.new_project()

            self.update_workspace_ui()
            self.update_title()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de charger l'espace de travail :\n{str(e)}")

    def add_current_tab_to_workspace(self):
        """ Ajoute la carte active à la playlist et sauvegarde immédiatement """
        if not self.current_workspace_path:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord ouvrir ou créer une workspace avec les boutons de gauche.")
            return

        ws = self.current_workspace()
        if not ws: return

        if not ws.current_file_path:
            QMessageBox.warning(self, "Action requise", "Sauvegardez d'abord ce fichier JSON sur votre disque (Ctrl+S) avant de l'ajouter.")
            return

        if ws.current_file_path in self.workspace_files:
            QMessageBox.information(self, "Information", "Cette carte est déjà incluse dans la workspace.")
            return

        self.workspace_files.append(ws.current_file_path)
        self.auto_save_workspace() # Sauvegarde automatique instantanée

    def remove_current_tab_from_workspace(self):
        """ Enlève la carte active de la workspace (sans fermer l'onglet) """
        if not self.current_workspace_path:
            return

        ws = self.current_workspace()
        if not ws or not ws.current_file_path: 
            return

        if ws.current_file_path in self.workspace_files:
            self.workspace_files.remove(ws.current_file_path)
            self.auto_save_workspace() # Sauvegarde automatique instantanée
        else:
            QMessageBox.warning(self, "Action impossible", "Ce fichier ne fait pas partie de la workspace.")

    def open_file(self):
        ws = self.current_workspace()
        if not ws: return
        sel = ws.scene.selectedItems()
        if len(sel) == 1 and isinstance(sel[0], NodeItem):
            node = sel[0]
            # Si le chemin est relatif, on le recompose à partir du dossier du JSON
            if not os.path.isabs(node.file_path) and ws.current_file_path:
                base_dir = os.path.dirname(ws.current_file_path)
                full_path = os.path.abspath(os.path.join(base_dir, node.file_path))
            else:
                full_path = node.file_path

            if os.path.exists(full_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
            else:
                QMessageBox.warning(self, "Erreur", "Le fichier joint est introuvable.")

    def new_project(self, force_empty=False):
        ws = MindMapWorkspace(self)
        root = NodeItem('root', 'Nouveau noeud', 0, 0, bg='#60A5FA', border='#3B82F6', font_color='#ffffff')
        root.signals.itemDoubleClicked.connect(self.start_inline_editing)
        root.signals.positionChanged.connect(self.save_state)
        ws.scene.addItem(root)
        
        self.tabs.addTab(ws, "[Nouveau Projet]")
        self.tabs.setCurrentWidget(ws)
        self.save_state()
        ws.is_dirty = False 
        self.update_title()

    def load_project(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ouvrir un ou plusieurs projets", "", "JSON (*.json)")
        if paths:
            for path in paths:
                self.load_project_from_path(path)

    def load_project_from_path(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            state_str = f.read()
            
        ws = MindMapWorkspace(self, path)
        self.tabs.addTab(ws, os.path.basename(path))
        self.tabs.setCurrentWidget(ws)
        
        self.apply_state(state_str)
        ws.undo_stack.append(state_str)
        ws.is_dirty = False
        
        self.settings.setValue("last_project_path", path)
        self.update_title()
        self.center_on_graph()

    def save_project(self, force_save_as=False):
        ws = self.current_workspace()
        if not ws: return False
        
        if not ws.current_file_path or force_save_as:
            nodes = [item for item in ws.scene.items() if isinstance(item, NodeItem)]
            root_node = next((n for n in nodes if n.node_id == 'root'), None)
            if root_node and root_node.label:
                default_name = root_node.label.replace('\n', ' ').strip()
                for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                    default_name = default_name.replace(char, '')
                if not default_name:
                    default_name = "ma_mindmap"
            else:
                default_name = "ma_mindmap"

            path, _ = QFileDialog.getSaveFileName(
                self, 
                "Enregistrer la carte", 
                f"{default_name}.json", 
                "Mind Map Files (*.json)"
            )
            if not path: return False
            ws.current_file_path = path
            
        with open(ws.current_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_state(), f, indent=2, ensure_ascii=False)
            
        ws.is_dirty = False
        self.settings.setValue("last_project_path", ws.current_file_path)
        self.update_title()
        return True
    
    def show_about_dialog(self):
        show_app_about_dialog(self, APP_VERSION)
        

    def apply_template(self, index):
        if index == 0: return
        ws = self.current_workspace()
        if not ws: return
        
        filename = self.template_combo.itemData(index)
        self.template_combo.setCurrentIndex(0)
        
        if QMessageBox.question(self, "Template", "Charger ce template remplacera la mind map de l'onglet actuel. Continuer ?") == QMessageBox.StandardButton.Yes:
            template_path = resource_path(os.path.join("templates", filename))
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                state_str = data["content"] if "content" in data else json.dumps(data)
                self.apply_state(state_str)
                ws.undo_stack.clear()
                ws.redo_stack.clear()
                ws.undo_stack.append(state_str)
                ws.is_dirty = True
                self.update_title()
                self.center_on_graph()
            else:
                QMessageBox.warning(self, "Erreur", f"Fichier template introuvable :\n{template_path}")

    def export_png(self):
        ws = self.current_workspace()
        if not ws: return
        default_name = "ma_mindmap.png"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PNG", default_name, "PNG (*.png)")
        if path:
            ws.scene.clearSelection()
            rect = ws.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            
            ratio = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else self.devicePixelRatio()
            
            pixmap = QPixmap(int(rect.width() * ratio), int(rect.height() * ratio))
            pixmap.setDevicePixelRatio(ratio)
            pixmap.fill(QColor('#f8f9fa'))
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            painter.scale(ratio, ratio)
            target_rect = QRectF(0, 0, rect.width(), rect.height())
            
            ws.scene.render(painter, target=target_rect, source=rect)
            painter.end()
            pixmap.save(path, "PNG", 100)

    def export_pdf(self):
        ws = self.current_workspace()
        if not ws: return
        
        default_name = "ma_mindmap.pdf"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.pdf"
            
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF Vectoriel", default_name, "PDF (*.pdf)")
        if path:
            ws.scene.clearSelection()
            
            # 1. On récupère les dimensions réelles occupées par le graphe (avec marge)
            rect = ws.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
            if rect.isEmpty(): return
            
            # 2. Utiliser ScreenResolution au lieu de HighResolution pour garder le bon ratio polices/formes
            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            
            # 3. Choix de l'orientation de la page
            layout = QPageLayout()
            if rect.width() > rect.height():
                layout.setOrientation(QPageLayout.Orientation.Landscape)
            else:
                layout.setOrientation(QPageLayout.Orientation.Portrait)
                
            layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            layout.setMargins(QMarginsF(10, 10, 10, 10))
            printer.setPageLayout(layout)
                
            painter = QPainter(printer)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # 4. Obtenir la zone de la page disponible en pixels de résolution logique
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            
            # 5. Calculer le ratio global pour que tout rentre proportionnellement
            scale_x = page_rect.width() / rect.width()
            scale_y = page_rect.height() / rect.height()
            scale = min(scale_x, scale_y)
            
            # 6. Définir un rectangle cible centré sur la page A4 qui respecte EXACTEMENT les proportions du graphe
            target_w = rect.width() * scale
            target_h = rect.height() * scale
            target_x = page_rect.left() + (page_rect.width() - target_w) / 2.0
            target_y = page_rect.top() + (page_rect.height() - target_h) / 2.0
            
            target_rect = QRectF(target_x, target_y, target_w, target_h)
            
            # 7. C'est scene.render() qui va gérer la mise à l'échelle harmonieuse des polices et des formes
            ws.scene.render(painter, target=target_rect, source=rect)
            painter.end()

    def export_md(self):
        ws = self.current_workspace()
        if not ws: return
        default_name = "ma_mindmap.md"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.md"
            
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Markdown", default_name, "Markdown (*.md)")
        if path:
            nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
            root = next((n for n in nodes if n.node_id == 'root'), nodes[0] if nodes else None)
            if not root: return
            
            output = []
            def build_tree(node, depth):
                clean_label = node.label.replace('\n', ' ')
                additions = []
                if node.file_path: additions.append(f"Fichier: {node.file_path}")
                if node.url_link: additions.append(f"URL: {node.url_link}")
                link_str = f" ({', '.join(additions)})" if additions else ""
                
                output.append(f"{'  ' * depth}- {clean_label}{link_str}")
                children = [e.dest_node for e in node.edges if e.source_node == node]
                for child in children: build_tree(child, depth + 1)
                    
            build_tree(root, 0)
            with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(output))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    # Forcer la mise à jour géométrique initiale de la barre de boutons dès l'affichage
    QTimer.singleShot(50, window.reposition_style_bar)
    sys.exit(app.exec())