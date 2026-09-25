import sys
import os
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QTabBar, QToolButton, QMenu
from PyQt6.QtGui import QFont, QIcon, QPainter, QColor
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal
from PyQt6 import sip

from services.updater_service import CURRENT_VERSION as APP_VERSION
from graphics.scene import MindMapWorkspace

from ui.menus import create_menus
from ui.toolbar import create_toolbar
from ui.shortcuts import setup_app_shortcuts
from ui.about_dialog import show_app_about_dialog
from ui.node_toolbar import create_node_toolbar
from ui.selection_manager import on_selection_changed
from ui.minimap import create_minimap
from ui.search_dialog import create_search_bar
from ui import theme

from services.serializer import MindMapSerializer
from services.history_service import HistoryService
from services.project_service import ProjectService

from controllers.editing_controller import EditingController
from controllers.graph_controller import GraphController
from controllers.style_controller import StyleController
from controllers.attachment_controller import AttachmentController
from controllers.export_controller import ExportController
from controllers.workspace_controller import WorkspaceController
from controllers.tools_controller import ToolsController
from controllers.routing_controller import RoutingController
from controllers.grid_controller import GridController
from controllers.tabs_controller import TabsController
from controllers.image_controller import ImageController
from controllers.notes_controller import NotesController
from controllers.import_controller import ImportController


class WorkspaceTabBar(QTabBar):
    """QTabBar qui dessine un petit trait de couleur en haut de chaque onglet faisant partie
    de l'espace de travail actif (au lieu d'une pastille dans l'onglet), et propose un menu
    contextuel (clic droit) pour ajouter/retirer l'onglet visé de l'espace de travail."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def paintEvent(self, event):
        super().paintEvent(event)
        app_window = self.window()
        wc = getattr(app_window, 'workspace_controller', None)
        tabs = getattr(app_window, 'tabs', None)
        if wc is None or tabs is None or not wc.workspace_files:
            return

        from ui import theme
        p = theme.get_palette(app_window)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(p['accent'])
        for i in range(self.count()):
            ws = tabs.widget(i)
            file_path = getattr(ws, 'current_file_path', None) if ws else None
            if file_path and file_path in wc.workspace_files:
                rect = self.tabRect(i)
                painter.fillRect(rect.x() + 3, rect.y() + 1, rect.width() - 6, 3, color)
        painter.end()

    def _show_context_menu(self, pos):
        index = self.tabAt(pos)
        if index < 0:
            return
        app_window = self.window()
        wc = getattr(app_window, 'workspace_controller', None)
        tabs = getattr(app_window, 'tabs', None)
        if wc is None or tabs is None:
            return

        tabs.setCurrentIndex(index)
        ws = tabs.widget(index)
        file_path = getattr(ws, 'current_file_path', None) if ws else None
        in_workspace = bool(file_path and file_path in wc.workspace_files)

        menu = QMenu(self)
        if in_workspace:
            menu.addAction("❌ Retirer de l'espace de travail", wc.remove_current_tab_from_workspace)
        else:
            menu.addAction("➕ Ajouter à l'espace de travail", wc.add_current_tab_to_workspace)
        menu.exec(self.mapToGlobal(pos))


class WorkspaceTabWidget(QTabWidget):
    """QTabWidget qui émet un signal au double-clic dans la zone vide de la ligne d'onglets
    (à côté des onglets existants, où la QTabBar interne ne couvre pas toute la largeur),
    pour créer rapidement un nouvel onglet — un geste très courant dans ce type d'outil
    (navigateurs, IDE...)."""
    emptyTabAreaDoubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(WorkspaceTabBar(self))

        # Petit bouton "+" collé juste après le dernier onglet (comme un navigateur/IDE),
        # plutôt qu'un gros bouton "Ajouter un onglet" isolé dans le coin de la fenêtre.
        self.add_tab_button = QToolButton(self)
        self.add_tab_button.setText("+")
        self.add_tab_button.setToolTip("Ajouter un onglet")
        self.add_tab_button.setAutoRaise(True)
        self.add_tab_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_tab_button.setFixedSize(24, 24)

    def _reposition_add_button(self):
        # bar.tabRect() est exprimé dans les coordonnées locales de la QTabBar, qui ne
        # commence plus à (0, 0) dans le QTabWidget depuis l'ajout du badge d'espace de
        # travail en coin haut-gauche (setCornerWidget) : il faut donc reprojeter via
        # bar.mapTo(self, ...) plutôt que d'utiliser les coordonnées locales telles quelles,
        # sans quoi le bouton "+" se retrouve décalé vers la gauche du dernier onglet.
        bar = self.tabBar()
        count = bar.count()
        if count > 0:
            last_rect = bar.tabRect(count - 1)
            anchor = bar.mapTo(self, last_rect.topRight())
            x = anchor.x() + 4
            y = anchor.y() + (last_rect.height() - self.add_tab_button.height()) // 2
        else:
            anchor = bar.mapTo(self, bar.rect().topLeft())
            x, y = anchor.x() + 4, anchor.y() + 4
        self.add_tab_button.move(x, max(0, y))
        self.add_tab_button.raise_()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._reposition_add_button()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._reposition_add_button()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_add_button()

    def mouseDoubleClickEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        bar = self.tabBar()
        # La QTabBar est positionnée en (0, 0) au sein du QTabWidget : ses coordonnées
        # locales correspondent donc directement à celles reçues ici tant qu'on reste
        # dans sa hauteur (au-delà, c'est le contenu de l'onglet, pas la barre).
        if pos.y() <= bar.height() and bar.tabAt(pos) == -1:
            self.emptyTabAreaDoubleClicked.emit()
            return
        super().mouseDoubleClickEvent(event)


class MindMapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mindy {APP_VERSION}")
        self.settings = QSettings("MindyApp", "MindMapEditor")
        self._clipboard_node = None

        self.current_workspace_path = None
        self.workspace_files = []

        # Initialisation des composants métiers / logiques d'abord
        self.project_service = ProjectService(self)
        self.history_service = HistoryService(self)
        self.serializer = MindMapSerializer(self)

        # Initialisation des contrôleurs
        self.graph_controller = GraphController(self)
        self.style_controller = StyleController(self)
        self.attachment_controller = AttachmentController(self)
        self.export_controller = ExportController(self)
        self.workspace_controller = WorkspaceController(self)
        self.tools_controller = ToolsController(self)
        self.editing_controller = EditingController(self)
        self.grid_controller = GridController(self)
        self.routing_controller = RoutingController(self)
        self.tabs_controller = TabsController(self)
        self.image_controller = ImageController(self)
        self.notes_controller = NotesController(self)
        self.import_controller = ImportController(self)

        # UI Principale
        self.tabs = WorkspaceTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setTabBarAutoHide(False) # Optionnel, mais utile
        self.tabs.setMovable(True) # Bonus sympa tant qu'à faire !
        self.tabs.tabCloseRequested.connect(self.tabs_controller.close_tab)
        self.tabs.currentChanged.connect(self.tabs_controller.on_tab_changed)
        self.tabs.emptyTabAreaDoubleClicked.connect(lambda: self.project_service.new_project())
        self.tabs.add_tab_button.clicked.connect(lambda: self.project_service.new_project())
        self.add_tab_button = self.tabs.add_tab_button  # référence conservée pour compat éventuelle

        # Badge/menu de l'espace de travail actif, au tout début de la barre d'onglets — la
        # liste des cartes elle-même n'affiche plus qu'un simple trait de couleur (WorkspaceTabBar)
        # sur les onglets qui en font partie, sans texte d'en-tête ni pastille par onglet.
        self.workspace_badge = QToolButton(self.tabs)
        self.workspace_badge.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.workspace_badge.setText("📁 Aucun espace de travail")
        self.workspace_badge.setAutoRaise(True)
        workspace_menu = QMenu(self.workspace_badge)
        workspace_menu.addAction("📄 Nouvel espace de travail    ", self.workspace_controller.new_workspace)
        workspace_menu.addAction("📂 Ouvrir un espace de travail    ", self.workspace_controller.load_workspace)
        self.workspace_badge.setMenu(workspace_menu)
        self.tabs.setCornerWidget(self.workspace_badge, Qt.Corner.TopLeftCorner)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1600, 900)
        
        self.setup_ui()
        self.setup_shortcuts()
        theme.apply_theme(self)

        # Un léger délai pour laisser l'interface s'afficher
        QTimer.singleShot(100, self.initialize_startup_session)

        # La vérification des mises à jour ne se fait plus automatiquement au lancement :
        # seulement à la demande, via "Vérifier les mises à jour" dans le menu À propos.

        # Sauvegarde automatique périodique des cartes déjà enregistrées sur disque
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_all_tabs)
        self.autosave_timer.start(3 * 60 * 1000)  # toutes les 3 minutes

    def initialize_startup_session(self):
        """Décide au démarrage s'il faut charger la workspace ou le dernier projet."""
        self._notify_if_just_updated()

        last_workspace = self.settings.value("last_collection_path", "")

        if last_workspace and os.path.exists(last_workspace):
            self.workspace_controller.load_workspace(last_workspace, is_startup=True)
        else:
            self.project_service.load_last_project_on_startup()

        # 🛡️ Sécurité : force une resynchronisation finale de la toolbar (canva, routage,
        # aimant) sur l'état réellement chargé, au cas où l'ordre des signaux internes
        # pendant le chargement au démarrage aurait laissé un widget désynchronisé.
        ws = self.current_workspace()
        if ws is not None and hasattr(self, 'workspace_controller'):
            self.workspace_controller.sync_workspace_ui({
                "snap_to_grid": getattr(ws.scene, 'snap_to_grid', False),
                "line_routing_mode": getattr(ws.scene, 'line_routing_mode', 'curved'),
                "canvas_type": getattr(ws.scene, 'canvas_type', 'none'),
                "canvas_scale": getattr(ws.scene, 'canvas_scale', 1.0),
            })

    def _notify_if_just_updated(self):
        """Affiche un message de confirmation propre si cette instance vient d'être lancée
        juste après une mise à jour (voir updater_service.perform_update, qui pose ce
        marqueur avant de relancer l'application) — plutôt que l'utilisateur ne découvre
        la mise à jour que par la nouvelle version affichée dans le menu À propos, ou pire,
        par l'éventuelle erreur transitoire du bootloader lors du relais automatique."""
        pending_version = self.settings.value("pending_update_version", "")
        if not pending_version:
            return
        self.settings.remove("pending_update_version")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Mise à jour réussie",
            f"Mindy a été mis à jour à la version {pending_version}."
        )

    def current_workspace(self) -> MindMapWorkspace:
        try:
            # Utilisation de sip pour s'assurer que l'objet C++ sous-jacent de Qt n'est pas mort
            if not hasattr(self, 'tabs') or self.tabs is None or sip.isdeleted(self.tabs):
                return None
            return self.tabs.currentWidget()
        except (RuntimeError, AttributeError):
            return None
   
    def setup_ui(self):
        self.setCentralWidget(self.tabs)
        create_menus(self)
        create_toolbar(self)
        create_node_toolbar(self)  # C'est ici que self.style_dock et self.overlay doivent être créés
        create_minimap(self)
        create_search_bar(self)

    def setup_shortcuts(self):
        setup_app_shortcuts(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay') and self.overlay is not None:
            self.overlay.raise_()
        if hasattr(self, 'minimap') and self.minimap is not None:
            self.minimap.reposition()
            self.minimap.raise_()
        if hasattr(self, 'search_bar') and self.search_bar is not None and self.search_bar.isVisible():
            self.search_bar.reposition()
            self.search_bar.raise_()

    def closeEvent(self, event):
        if hasattr(self, 'tools_controller'):
            self.tools_controller.handle_close_event(event)
        else:
            event.accept()

    def save_state(self):
        ws = self.current_workspace()
        if not ws:
            return

        if getattr(ws, 'is_applying_state', False):
            return

        current_state = self.serializer.get_state()
        self.history_service.save_state(ws, current_state)
        self.tabs_controller.update_title()
        self.refresh_undo_redo_state()

    def show_about_dialog(self):
        show_app_about_dialog(self, APP_VERSION)

    def undo(self):
        ws = self.current_workspace()
        if ws:
            previous_state = self.history_service.undo(ws)
            if previous_state:
                self.serializer.apply_state(previous_state)
        self.refresh_undo_redo_state()

    def redo(self):
        ws = self.current_workspace()
        if ws:
            next_state = self.history_service.redo(ws)
            if next_state:
                self.serializer.apply_state(next_state)
        self.refresh_undo_redo_state()

    def refresh_undo_redo_state(self):
        """Active/désactive les actions Annuler/Rétablir selon le contenu de la pile d'historique."""
        ws = self.current_workspace()
        can_undo = bool(ws and len(getattr(ws, 'undo_stack', [])) >= 2)
        can_redo = bool(ws and len(getattr(ws, 'redo_stack', [])) > 0)

        if hasattr(self, 'undo_action') and self.undo_action is not None:
            self.undo_action.setEnabled(can_undo)
        if hasattr(self, 'redo_action') and self.redo_action is not None:
            self.redo_action.setEnabled(can_redo)

    def autosave_all_tabs(self):
        """Sauvegarde silencieusement sur disque les onglets déjà nommés qui ont des modifications non enregistrées."""
        if not hasattr(self, 'tabs') or self.tabs is None:
            return

        for i in range(self.tabs.count()):
            ws = self.tabs.widget(i)
            if not ws or not getattr(ws, 'is_dirty', False):
                continue

            file_path = getattr(ws, 'current_file_path', None)
            if not file_path:
                continue  # Onglet jamais enregistré manuellement : on ne force pas de "Enregistrer sous"

            try:
                state_to_save = self.serializer.get_state(ws)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_to_save, f, indent=2, ensure_ascii=False)
                ws.is_dirty = False
                self.tabs_controller.update_title(i)
            except Exception as e:
                print(f"[Autosave] Échec de la sauvegarde automatique de '{file_path}' : {e}")
        
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MindMapApp()
    window.show()
    sys.exit(app.exec())