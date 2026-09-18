import os
import shutil
from PyQt6.QtWidgets import QLabel, QPushButton, QComboBox, QWidget, QLineEdit, QSizePolicy, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from services.template_service import refresh_template_combo
from graphics.canvas_backgrounds import CANVAS_TYPES
from ui import theme

CANVAS_SCALE_MIN = 0.6
CANVAS_SCALE_MAX = 3.0
CANVAS_SCALE_STEP = 0.2


def _set_canvas_scale(app_window, delta):
    ws = app_window.current_workspace()
    if not ws:
        return
    current = getattr(ws.scene, 'canvas_scale', 1.0)
    new_scale = round(min(CANVAS_SCALE_MAX, max(CANVAS_SCALE_MIN, current + delta)), 2)
    if new_scale == current:
        return
    ws.scene.canvas_scale = new_scale
    ws.scene.update()
    _refresh_canvas_scale_label(app_window)
    if hasattr(app_window, 'save_state'):
        app_window.save_state()


def _refresh_canvas_scale_label(app_window):
    if not hasattr(app_window, 'canvas_scale_label'):
        return
    ws = app_window.current_workspace()
    scale = getattr(ws.scene, 'canvas_scale', 1.0) if ws else 1.0
    app_window.canvas_scale_label.setText(f"{int(round(scale * 100))}%")


def _load_canvas_image(app_window):
    """Ouvre un sélecteur de fichier, copie l'image choisie localement et l'affecte comme fond du canva actif."""
    ws = app_window.current_workspace()
    if not ws:
        return False

    file_path, _ = QFileDialog.getOpenFileName(
        app_window, "Choisir une image de fond", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
    )
    if not file_path:
        return False

    try:
        target_dir = os.path.abspath(".mindmap_attachments")
        os.makedirs(target_dir, exist_ok=True)

        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        counter = 1
        new_name = base_name
        while os.path.exists(os.path.join(target_dir, new_name)):
            new_name = f"{name}_{counter}{ext}"
            counter += 1

        dest_path = os.path.join(target_dir, new_name)
        shutil.copy(file_path, dest_path)

        ws.scene.canvas_image_path = dest_path
        ws.scene.canvas_type = 'custom'
        ws.scene._canvas_image_cache.pop(dest_path, None)
        ws.scene.update()

        if hasattr(app_window, 'canvas_combo') and app_window.canvas_combo is not None:
            idx = app_window.canvas_combo.findData('custom')
            if idx >= 0:
                app_window.canvas_combo.blockSignals(True)
                app_window.canvas_combo.setCurrentIndex(idx)
                app_window.canvas_combo.blockSignals(False)

        if hasattr(app_window, 'save_state'):
            app_window.save_state()
        return True
    except Exception as e:
        QMessageBox.critical(app_window, "Erreur", f"Impossible de charger l'image :\n{e}")
        return False

def create_toolbar(app_window) -> None:
    """
    Initialise et configure la barre d'outils supérieure de l'espace de travail
    avec le support des types de Canvas et des 4 modes de routage de lignes.
    """
    # Vérification stricte des dépendances indispensables
    required_attrs = [
        'workspace_controller', 'project_service', 'grid_controller', 
        'routing_controller', 'tools_controller', 'tabs'
    ]
    for attr in required_attrs:
        if not hasattr(app_window, attr) or getattr(app_window, attr) is None:
            raise AttributeError(
                f"Erreur d'initialisation de la Toolbar : '{attr}' doit être configuré "
                f"sur app_window avant d'appeler create_toolbar."
            )

    # Configuration et styles de la barre d'outils
    workspace_toolbar = app_window.addToolBar("workspace")
    workspace_toolbar.setMovable(False)
    app_window.workspace_toolbar = workspace_toolbar
    workspace_toolbar.setStyleSheet(theme.toolbar_stylesheet(theme.get_palette(app_window)))

    # Label de statut
    if hasattr(app_window, 'lbl_workspace_status'):
        workspace_toolbar.addWidget(app_window.lbl_workspace_status)
    workspace_toolbar.addSeparator()

    # Actions d'onglets au sein de l'espace de travail
    btn_add_to_coll = QPushButton("➕", workspace_toolbar)
    btn_add_to_coll.setToolTip("Inclure l'onglet actuel dans l'espace de travail")
    
    btn_remove_from_coll = QPushButton("❌", workspace_toolbar)
    btn_remove_from_coll.setToolTip("Retirer l'onglet actuel de l'espace de travail")
    
    workspace_toolbar.addWidget(btn_add_to_coll)
    workspace_toolbar.addWidget(btn_remove_from_coll)
    
    btn_add_to_coll.clicked.connect(app_window.workspace_controller.add_current_tab_to_workspace)
    btn_remove_from_coll.clicked.connect(app_window.workspace_controller.remove_current_tab_from_workspace)
    
    workspace_toolbar.addSeparator()

    # Bouton Sauvegarder
    btn_save = QPushButton("💾", workspace_toolbar)
    btn_save.setToolTip("Sauvegarder")
    btn_save.clicked.connect(app_window.project_service.save_project) 
    workspace_toolbar.addWidget(btn_save)

    # Remplacement de l'ancien bouton unique "Liens courbes" par le sélecteur à 4 choix de routage
    app_window.routing_mode_combo = QComboBox(workspace_toolbar)
    app_window.routing_mode_combo.addItem("Liens Courbes", "curved")
    app_window.routing_mode_combo.addItem("Liens Ortho", "orthogonal")
    app_window.routing_mode_combo.addItem("Liens Droits", "straight_diagonal")
    app_window.routing_mode_combo.addItem("Liens Coudés", "straight_elbow")
    app_window.routing_mode_combo.setToolTip("Choisir la forme géométrique des arêtes")

    def on_routing_mode_changed(index):
        mode = app_window.routing_mode_combo.itemData(index)
        if hasattr(app_window, 'routing_controller'):
            app_window.routing_controller.set_routing_mode(mode)

    app_window.routing_mode_combo.currentIndexChanged.connect(on_routing_mode_changed)
    workspace_toolbar.addWidget(app_window.routing_mode_combo)

    # Bouton Aimant Grille (Toggle)
    app_window.btn_snap = QPushButton(" 🧲 Aimant ", workspace_toolbar)
    app_window.btn_snap.setCheckable(True)
    app_window.btn_snap.setStyleSheet(theme.toggle_button_stylesheet(theme.get_palette(app_window)))

    app_window.btn_snap.clicked.connect(app_window.grid_controller.toggle_snap_to_grid)
    workspace_toolbar.addWidget(app_window.btn_snap)

    workspace_toolbar.addSeparator()
    
    # ComboBox des modèles (Templates), peuplée dynamiquement depuis le dossier des templates
    app_window.template_combo = QComboBox(workspace_toolbar)
    refresh_template_combo(app_window)

    app_window.template_combo.currentIndexChanged.connect(
        lambda idx, window=app_window: window.tools_controller.apply_template(idx)
    )
    workspace_toolbar.addWidget(app_window.template_combo)

    app_window.canvas_combo = QComboBox(workspace_toolbar)
    for key, label in CANVAS_TYPES.items():
        app_window.canvas_combo.addItem(label, key)
    app_window.canvas_combo.setToolTip("Choisir un canva de fond (Kanban, matrices, etc.)")

    def on_canvas_changed(index):
        ws = app_window.current_workspace()
        if not ws:
            return
        canvas_key = app_window.canvas_combo.itemData(index)

        if canvas_key == 'custom':
            loaded = _load_canvas_image(app_window)
            if not loaded and not getattr(ws.scene, 'canvas_image_path', None):
                # L'utilisateur a annulé et il n'y avait pas déjà d'image : on revient à "Aucun canva"
                app_window.canvas_combo.blockSignals(True)
                app_window.canvas_combo.setCurrentIndex(app_window.canvas_combo.findData('none'))
                app_window.canvas_combo.blockSignals(False)
            return

        ws.scene.canvas_type = canvas_key
        ws.scene.update()
        if hasattr(app_window, 'save_state'):
            app_window.save_state()

    app_window.canvas_combo.currentIndexChanged.connect(on_canvas_changed)
    workspace_toolbar.addWidget(app_window.canvas_combo)

    # Contrôles de taille du canva (agrandir/réduire par pas, distinct du zoom de la vue)
    btn_canvas_smaller = QPushButton("➖", workspace_toolbar)
    btn_canvas_smaller.setToolTip("Réduire la taille du canva de fond")
    btn_canvas_smaller.clicked.connect(lambda: _set_canvas_scale(app_window, -CANVAS_SCALE_STEP))
    workspace_toolbar.addWidget(btn_canvas_smaller)

    app_window.canvas_scale_label = QLabel("100%", workspace_toolbar)
    app_window.canvas_scale_label.setToolTip("Taille actuelle du canva de fond")
    app_window.canvas_scale_label.setMinimumWidth(36)
    app_window.canvas_scale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    workspace_toolbar.addWidget(app_window.canvas_scale_label)

    btn_canvas_bigger = QPushButton("➕", workspace_toolbar)
    btn_canvas_bigger.setToolTip("Agrandir la taille du canva de fond (plus de place pour les nœuds)")
    btn_canvas_bigger.clicked.connect(lambda: _set_canvas_scale(app_window, CANVAS_SCALE_STEP))
    workspace_toolbar.addWidget(btn_canvas_bigger)

    workspace_toolbar.addSeparator()

    # Bouton Auto Center
    btn_center = QPushButton("Centrer", workspace_toolbar)
    btn_center.setToolTip("Centrer la vue sur le nœud principal")
    btn_center.setStyleSheet("""
        QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; }
        QPushButton:hover { background-color: #2563EB; }
    """)
    btn_center.clicked.connect(app_window.tools_controller.auto_center_clicked)
    workspace_toolbar.addWidget(btn_center)

    # Bouton Ajuster à l'écran (fit-to-view)
    btn_fit = QPushButton("🔍 Ajuster", workspace_toolbar)
    btn_fit.setToolTip("Ajuster le zoom pour voir l'ensemble de la carte")
    btn_fit.setStyleSheet("""
            QPushButton { background-color: #0EA5E9; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; }
            QPushButton:hover { background-color: #0284C7; }
    """)
    btn_fit.clicked.connect(app_window.tools_controller.fit_to_view_clicked)
    workspace_toolbar.addWidget(btn_fit)

    # Bouton Réorganisation auto (réalignement propre et instantané de l'arborescence)
    btn_auto_layout = QPushButton("🧹 Réorganiser", workspace_toolbar)
    btn_auto_layout.setToolTip("Réaligner proprement l'arborescence à partir du nœud central")
    btn_auto_layout.setStyleSheet("""
        QPushButton { background-color: #8B5CF6; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; }
        QPushButton:hover { background-color: #7C3AED; }
    """)
    btn_auto_layout.clicked.connect(app_window.graph_controller.auto_layout)
    workspace_toolbar.addWidget(btn_auto_layout)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    workspace_toolbar.addWidget(spacer)

    workspace_toolbar.addWidget(QLabel(" 🔍  "))
    app_window.search_input = QLineEdit()
    search_input = app_window.search_input
    search_input.setPlaceholderText("Rechercher un nœud... (Ctrl+F)")
    search_input.setMaximumWidth(200)
    search_input.setClearButtonEnabled(True)
    search_input.textChanged.connect(app_window.graph_controller.filter_nodes)
    workspace_toolbar.addWidget(search_input)

    # ==========================================
    # DEUXIÈME RANGÉE : Canva de fond + Réorganisation auto
    # Sur sa propre rangée (addToolBarBreak) pour ne jamais être poussée dans le menu
    # de débordement "»" de la barre principale, déjà bien chargée.
    # ==========================================
    #app_window.addToolBarBreak()
    #canvas_toolbar = app_window.addToolBar("canvas")
    #canvas_toolbar.setMovable(False)
    #canvas_toolbar.setStyleSheet(workspace_toolbar.styleSheet())

    # Bouton Ajouter un onglet inséré dans le coin supérieur droit du QTabWidget
    app_window.add_tab_button = QPushButton("➕ Ajouter un onglet", app_window.tabs)
    app_window.add_tab_button.clicked.connect(app_window.project_service.new_project)
    app_window.tabs.setCornerWidget(app_window.add_tab_button, Qt.Corner.TopRightCorner)