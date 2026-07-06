from PyQt6.QtWidgets import QLabel, QPushButton, QComboBox, QWidget, QLineEdit, QSizePolicy
from PyQt6.QtCore import Qt

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
    workspace_toolbar.setStyleSheet("""
        QToolBar { background: #F1F5F9; border-bottom: 1px solid #CBD5E1; padding: 4px; spacing: 8px; }
        QPushButton { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 12px; color: #1e293b; }
        QPushButton:hover { background: #E2E8F0; }
        QLabel { font-size: 11px; color: #475569; font-weight: bold; }
        QComboBox { border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 6px; background: white; color: #1e293b; font-size: 12px; min-width: 130px; }
        QComboBox:hover { border-color: #94a3b8; }
    """)

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

    # Bouton Aimant Grille (Toggle)
    app_window.btn_snap = QPushButton(" 🧲 Aimant Grille ", workspace_toolbar)
    app_window.btn_snap.setCheckable(True)
    app_window.btn_snap.setStyleSheet("""
        QPushButton { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #f1f5f9; color: #1e293b; }
        QPushButton:checked { background: #3B82F6; color: white; border-color: #2563EB; font-weight: bold; }
    """)
    app_window.btn_snap.clicked.connect(app_window.grid_controller.toggle_snap_to_grid)
    workspace_toolbar.addWidget(app_window.btn_snap)

    workspace_toolbar.addSeparator()

    # Remplacement de l'ancien bouton unique "Liens courbes" par le sélecteur à 4 choix de routage
    app_window.routing_mode_combo = QComboBox(workspace_toolbar)
    app_window.routing_mode_combo.addItem("Liens Courbes", "curved")
    app_window.routing_mode_combo.addItem("Liens Orthogonaux", "orthogonal")
    app_window.routing_mode_combo.addItem("Liens Diagonaux", "straight_diagonal")
    app_window.routing_mode_combo.addItem("Liens Coudés", "straight_elbow")
    app_window.routing_mode_combo.setToolTip("Choisir la forme géométrique des arêtes")

    def on_routing_mode_changed(index):
        mode = app_window.routing_mode_combo.itemData(index)
        if hasattr(app_window, 'routing_controller'):
            app_window.routing_controller.set_routing_mode(mode)

    app_window.routing_mode_combo.currentIndexChanged.connect(on_routing_mode_changed)
    workspace_toolbar.addWidget(app_window.routing_mode_combo)

    workspace_toolbar.addSeparator()
    
    # ComboBox des modèles (Templates)
    app_window.template_combo = QComboBox(workspace_toolbar)
    app_window.template_combo.addItem("Choisir un template...")
    app_window.template_combo.addItem("🎯 Cadrage d'Idée", "cadrage_idee.json")
    app_window.template_combo.addItem("🔍 Résolution de Problème", "resolution_probleme.json")
    app_window.template_combo.addItem("⏳ Organisation des priorités", "gestion_temps.json")
    app_window.template_combo.addItem("🧠 Brain Dump", "brain_dump.json")
    app_window.template_combo.addItem("🚀 Onboarding Technique", "onboarding_technique.json")
    app_window.template_combo.addItem("🎨 Hub Multi-Passions", "hub_passions.json")
    app_window.template_combo.addItem("✈️ Organisation d'un Voyage", "organisation_voyage.json")
    app_window.template_combo.addItem("🗣️ Préparation Réunion", "preparation_reunion.json")
    app_window.template_combo.addItem("🏁 Rétrospective de Fin de Projet", "retro_projet.json")
    app_window.template_combo.addItem("☀️ Daily Capsule", "daily_capsule.json")
    app_window.template_combo.addItem("🔋 Santé Mentale et Énergie", "sante_mentale_energie.json")
    app_window.template_combo.addItem("🚨 Urgence Colère", "urgence_colere.json")
    
    app_window.template_combo.currentIndexChanged.connect(
        lambda idx, window=app_window: window.tools_controller.apply_template(idx)
    )
    workspace_toolbar.addWidget(app_window.template_combo)
    
    # Bouton Auto Center
    btn_center = QPushButton("Auto Center", workspace_toolbar)
    btn_center.setToolTip("Centrer la vue sur le nœud principal")
    btn_center.setStyleSheet("""
        QPushButton { background-color: #3B82F6; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; }
        QPushButton:hover { background-color: #2563EB; }
    """)
    btn_center.clicked.connect(app_window.tools_controller.auto_center_clicked)
    workspace_toolbar.addWidget(btn_center)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    workspace_toolbar.addWidget(spacer)
    
    workspace_toolbar.addWidget(QLabel(" 🔍  "))
    search_input = QLineEdit()
    search_input.setPlaceholderText("Rechercher un nœud...")
    search_input.setMaximumWidth(200)
    search_input.setClearButtonEnabled(True)
    search_input.textChanged.connect(app_window.graph_controller.filter_nodes)
    workspace_toolbar.addWidget(search_input)

    # Bouton Ajouter un onglet inséré dans le coin supérieur droit du QTabWidget
    app_window.add_tab_button = QPushButton("➕ Ajouter un onglet", app_window.tabs)
    app_window.add_tab_button.clicked.connect(app_window.project_service.new_project)
    app_window.tabs.setCornerWidget(app_window.add_tab_button, Qt.Corner.TopRightCorner)