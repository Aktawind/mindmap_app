from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QFrame, QComboBox, QDockWidget, QScrollArea
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from graphics.items import NODE_FORMATS
from ui.collapsible_section import CollapsibleSection
from ui import theme

# Couleurs de base proposées pour les nœuds (remplissage, bordure), déclinées en variantes
# assombries en thème sombre via theme.adapt_fill() pour rester lisibles sur fond sombre.
PRESET_NODE_COLORS = [
    ('#60A5FA', '#3B82F6'), ('#E0F7FA', '#4DD0E1'),
    ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'),
    ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')
]


def _build_preset_color_buttons(app_window, grid_widget, grid_layout, columns):
    """(Re)construit les pastilles de couleurs de base des nœuds, en les assombrissant si le
    thème sombre est actif, pour un rendu correct sur fond sombre. Appelé à la création du
    panneau puis à chaque bascule de thème (voir theme.apply_theme)."""
    while grid_layout.count():
        item = grid_layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()

    dark = theme.is_dark_mode(app_window)
    for i, (color, border) in enumerate(PRESET_NODE_COLORS):
        display_color = theme.adapt_fill(color, dark).name()
        btn = QPushButton(grid_widget)
        btn.setFixedSize(22, 22)
        btn.setStyleSheet(f"background: {display_color}; border: 2px solid {border}; border-radius: 11px;")
        btn.clicked.connect(lambda _, c=display_color, b=border: app_window.style_controller.change_color(c, b))
        grid_layout.addWidget(btn, *divmod(i, columns))


def _labeled_row(parent, label_text, widget):
    """Empile un petit label au-dessus d'un widget, pour une lecture plus claire dans le panneau vertical."""
    app_window = parent.window() if hasattr(parent, 'window') else None
    p = theme.get_palette(app_window)
    row = QWidget(parent)
    row_layout = QVBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(2)
    label = QLabel(label_text, row)
    label.setStyleSheet(f"color: {p['text_muted']}; font-size: 11px;")
    row_layout.addWidget(label)
    row_layout.addWidget(widget)
    return row


def create_node_toolbar(app_window) -> None:
    """
    Construit le panneau latéral (dock) des propriétés de nœud/branche, organisé en
    sections repliables, ainsi que l'overlay d'aide pour la fenêtre principale.
    """
    # Vérification de sécurité des dépendances requises sur l'objet parent
    required_controllers = [
        'style_controller', 'attachment_controller',
        'editing_controller', 'routing_controller', 'graph_controller'
    ]
    for controller in required_controllers:
        if not hasattr(app_window, controller) or getattr(app_window, controller) is None:
            raise AttributeError(
                f"Erreur d'initialisation : '{controller}' doit être configuré sur "
                f"app_window avant d'appeler create_node_toolbar."
            )

    settings = getattr(app_window, 'settings', None)
    palette = theme.get_palette(app_window)

    # 1. Le panneau latéral (QDockWidget) qui accueille toutes les sections de propriétés
    app_window.style_dock = QDockWidget("Propriétés", app_window)
    app_window.style_dock.setObjectName("PropertiesDock")
    app_window.style_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
    app_window.style_dock.setMinimumWidth(230)

    panel = QWidget(app_window.style_dock)
    panel.setObjectName("PropertiesPanel")
    panel.setStyleSheet(theme.panel_stylesheet(palette))
    app_window.properties_panel = panel
    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(8, 8, 8, 8)
    panel_layout.setSpacing(4)

    # 2. Section : Liaison Inter-nœuds (Connect Controls) — mise en avant en haut du panneau
    app_window.connect_controls = QWidget(panel)
    cc_layout = QHBoxLayout(app_window.connect_controls)
    cc_layout.setContentsMargins(0, 0, 0, 8)
    app_window.btn_connect_nodes = QPushButton("🔗 Relier les nœuds", app_window.connect_controls)
    app_window.btn_connect_nodes.setStyleSheet(theme.connect_button_stylesheet(palette))
    app_window.btn_connect_nodes.clicked.connect(app_window.graph_controller.connect_selected_nodes)
    cc_layout.addWidget(app_window.btn_connect_nodes)
    panel_layout.addWidget(app_window.connect_controls)

    # 3. Section : Contrôles des Nœuds (Node Controls), regroupés en sous-sections repliables
    app_window.node_controls = QWidget(panel)
    nc_layout = QVBoxLayout(app_window.node_controls)
    nc_layout.setContentsMargins(0, 0, 0, 0)
    nc_layout.setSpacing(0)

    def add_section(title, settings_key, start_expanded=True):
        section = CollapsibleSection(title, app_window.node_controls, settings=settings,
                                      settings_key=settings_key, start_expanded=start_expanded)
        nc_layout.addWidget(section)
        return section

    # 3a. Texte
    section_text = add_section("✏️ Texte", "panel_section_text")
    text_row = QWidget(section_text)
    text_row_layout = QHBoxLayout(text_row)
    text_row_layout.setContentsMargins(0, 0, 0, 0)

    btn_bold = QPushButton("Bold", text_row)
    btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    btn_bold.setFixedSize(45, 26)
    btn_bold.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_bold.clicked.connect(app_window.style_controller.toggle_bold)
    text_row_layout.addWidget(btn_bold)

    btn_italic = QPushButton("Italic", text_row)
    font_it = QFont("Arial", 10)
    font_it.setItalic(True)
    btn_italic.setFont(font_it)
    btn_italic.setFixedSize(45, 26)
    btn_italic.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_italic.clicked.connect(app_window.style_controller.toggle_italic)
    text_row_layout.addWidget(btn_italic)

    btn_strike = QPushButton("Strike", text_row)
    font_st = QFont("Arial", 10)
    font_st.setStrikeOut(True)
    btn_strike.setFont(font_st)
    btn_strike.setFixedSize(45, 26)
    btn_strike.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_strike.clicked.connect(app_window.style_controller.toggle_strikethrough)
    text_row_layout.addWidget(btn_strike)
    text_row_layout.addStretch()
    section_text.add_widget(text_row)

    # 3b. Forme & Format
    section_shape = add_section("🔷 Forme et Format", "panel_section_shape")

    app_window.shape_combo = QComboBox(section_shape)
    app_window.shape_combo.addItem("Rectangle", "box")
    app_window.shape_combo.addItem("Losange", "diamond")
    app_window.shape_combo.addItem("Ellipse", "ellipse")
    app_window.shape_combo.addItem("Parallélogramme", "parallelogram")
    app_window.shape_combo.currentIndexChanged.connect(app_window.style_controller.on_shape_combo_changed)
    section_shape.add_widget(_labeled_row(section_shape, "Forme", app_window.shape_combo))

    app_window.format_combo = QComboBox(section_shape)
    app_window.format_combo.setToolTip("Format du nœud (taille et police)")
    for key, fmt in NODE_FORMATS.items():
        app_window.format_combo.addItem(fmt['label'], key)
    app_window.format_combo.currentIndexChanged.connect(app_window.style_controller.on_format_combo_changed)
    section_shape.add_widget(_labeled_row(section_shape, "Format", app_window.format_combo))

    # 3c. Statut & Priorité
    section_status = add_section("🚦 Statut et Priorité", "panel_section_status")

    app_window.status_combo = QComboBox(section_status)
    app_window.status_combo.addItem("⚪ Aucun statut", "none")
    app_window.status_combo.addItem("🚨 Urgent", "urgent")
    app_window.status_combo.addItem("⏳ En cours", "progress")
    app_window.status_combo.addItem("✅ Terminé", "done")
    app_window.status_combo.currentIndexChanged.connect(app_window.style_controller.on_status_combo_changed)
    section_status.add_widget(_labeled_row(section_status, "Statut", app_window.status_combo))

    app_window.priority_combo = QComboBox(section_status)
    app_window.priority_combo.addItem("⚪️ Priorité Normale", "none")
    app_window.priority_combo.addItem("🟡 Priorité Moyenne", "mid")
    app_window.priority_combo.addItem("🔴 Priorité Haute", "high")
    if hasattr(app_window.style_controller, 'on_priority_combo_changed'):
        app_window.priority_combo.currentIndexChanged.connect(app_window.style_controller.on_priority_combo_changed)
    section_status.add_widget(_labeled_row(section_status, "Priorité", app_window.priority_combo))

    app_window.btn_set_date = QPushButton("📅 Échéance", section_status)
    if hasattr(app_window.style_controller, 'prompt_node_date'):
        app_window.btn_set_date.clicked.connect(app_window.style_controller.prompt_node_date)
    section_status.add_widget(app_window.btn_set_date)

    app_window.btn_compact = QPushButton("🗜️ Mode compact", section_status)
    app_window.btn_compact.setCheckable(True)
    if hasattr(app_window.style_controller, 'toggle_compact_mode'):
        app_window.btn_compact.clicked.connect(app_window.style_controller.toggle_compact_mode)
    section_status.add_widget(app_window.btn_compact)

    # 3d. Couleurs
    section_colors = add_section("🎨 Couleurs", "panel_section_colors", start_expanded=False)
    COLOR_GRID_COLUMNS = 6

    preset_grid_widget = QWidget(section_colors)
    preset_grid = QGridLayout(preset_grid_widget)
    preset_grid.setContentsMargins(0, 0, 0, 0)
    preset_grid.setSpacing(4)
    app_window.preset_colors_widget = preset_grid_widget
    app_window.preset_colors_layout = preset_grid
    app_window.refresh_preset_colors = lambda: _build_preset_color_buttons(
        app_window, preset_grid_widget, preset_grid, COLOR_GRID_COLUMNS
    )
    app_window.refresh_preset_colors()
    section_colors.add_widget(preset_grid_widget)

    # Palette de couleurs personnalisées (ajoutées par l'utilisateur, sauvegardées, supprimables)
    app_window.custom_colors_widget = QWidget(section_colors)
    app_window.custom_colors_layout = QGridLayout(app_window.custom_colors_widget)
    app_window.custom_colors_layout.setContentsMargins(0, 0, 0, 0)
    app_window.custom_colors_layout.setSpacing(4)
    section_colors.add_widget(app_window.custom_colors_widget)

    btn_add_custom_color = QPushButton("+ Ajouter une couleur", section_colors)
    btn_add_custom_color.setToolTip("Ajouter une couleur personnalisée à la palette")
    btn_add_custom_color.setStyleSheet(
        "QPushButton { border: 2px dashed #94A3B8; font-weight: bold; color: #64748B; } "
        "QPushButton:hover { background: #E2E8F0; }"
    )
    btn_add_custom_color.clicked.connect(app_window.style_controller.add_custom_color)
    section_colors.add_widget(btn_add_custom_color)

    app_window.style_controller.refresh_custom_color_buttons()

    # 3e. Pièces jointes & Notes
    section_attach = add_section("📎 Pièces jointes", "panel_section_attach", start_expanded=False)

    btn_attach = QPushButton("📎 Fichier", section_attach)
    btn_attach.clicked.connect(app_window.attachment_controller.attach_file)
    section_attach.add_widget(btn_attach)

    btn_url = QPushButton("🔗 URL", section_attach)
    btn_url.clicked.connect(app_window.attachment_controller.attach_url)
    section_attach.add_widget(btn_url)

    btn_mindmap_link = QPushButton("🗺️ Lien vers un mindmap", section_attach)
    btn_mindmap_link.setToolTip("Lier ce nœud à un autre fichier mindmap (.mindy)")
    btn_mindmap_link.clicked.connect(app_window.attachment_controller.attach_mindmap_link)
    section_attach.add_widget(btn_mindmap_link)

    btn_img = QPushButton("🏞️ Image", section_attach)
    btn_img.clicked.connect(app_window.image_controller.attach_image_to_selected)
    section_attach.add_widget(btn_img)

    btn_notes = QPushButton("📝 Notes", section_attach)
    btn_notes.setToolTip("Ouvrir les notes détaillées du nœud")
    btn_notes.clicked.connect(lambda: app_window.notes_controller.open_notes_dialog())
    section_attach.add_widget(btn_notes)

    # Petit bouton bonus pour redimensionner la hauteur de l'image du nœud
    app_window.btn_img_h = QPushButton("↕️ Hauteur de l'image", section_attach)
    app_window.btn_img_h.setToolTip("Modifier la hauteur de l'image")
    app_window.btn_img_h.clicked.connect(app_window.image_controller.change_image_height)
    section_attach.add_widget(app_window.btn_img_h)

    app_window.btn_detach = QPushButton("❌ Dissocier", section_attach)
    app_window.btn_detach.setStyleSheet(theme.danger_button_stylesheet(palette))
    app_window.btn_detach.clicked.connect(app_window.attachment_controller.detach_links)
    section_attach.add_widget(app_window.btn_detach)

    panel_layout.addWidget(app_window.node_controls)

    # 4. Section : Contrôles des Branches (Edge Controls)
    app_window.edge_controls = QWidget(panel)
    ec_layout = QVBoxLayout(app_window.edge_controls)
    ec_layout.setContentsMargins(0, 8, 0, 0)
    ec_layout.setSpacing(6)

    ec_title = QLabel("<b>🔗 Branche</b>", app_window.edge_controls)
    ec_layout.addWidget(ec_title)

    btn_edit_edge = QPushButton("Texte de branche", app_window.edge_controls)
    btn_edit_edge.clicked.connect(app_window.editing_controller.edit_selected_edge)
    ec_layout.addWidget(btn_edit_edge)

    app_window.arrow_combo = QComboBox(app_window.edge_controls)
    app_window.arrow_combo.addItem("➖ Aucune flèche", "none")
    app_window.arrow_combo.addItem("➡️ Flèche Avant", "forward")
    app_window.arrow_combo.addItem("⬅️ Flèche Arrière", "backward")
    app_window.arrow_combo.addItem("↔️ Double flèche", "both")
    app_window.arrow_combo.currentIndexChanged.connect(app_window.routing_controller.on_arrow_combo_changed)
    ec_layout.addWidget(app_window.arrow_combo)

    panel_layout.addWidget(app_window.edge_controls)
    panel_layout.addStretch()

    scroll_area = QScrollArea(app_window.style_dock)
    scroll_area.setWidget(panel)
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    app_window.style_dock.setWidget(scroll_area)

    app_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, app_window.style_dock)
    app_window.style_dock.hide()

    if hasattr(app_window, 'display_menu') and app_window.display_menu is not None:
        toggle_dock_action = app_window.style_dock.toggleViewAction()
        toggle_dock_action.setText("Afficher le panneau de propriétés")
        app_window.display_menu.addAction(toggle_dock_action)

    # 5. Overlay d'aide contextuel
    app_window.overlay = QFrame(app_window)
    app_window.overlay.setStyleSheet(theme.overlay_stylesheet(palette))
    ol_layout = QVBoxLayout(app_window.overlay)

    ol_header = QHBoxLayout()
    ol_header.setContentsMargins(0, 0, 0, 0)
    ol_title = QLabel("<b>Commandes :</b>", app_window.overlay)
    ol_header.addWidget(ol_title)
    ol_header.addStretch()
    btn_close_overlay = QPushButton("✕", app_window.overlay)
    btn_close_overlay.setFixedSize(18, 18)
    btn_close_overlay.setStyleSheet(
        "QPushButton { padding: 0px; margin: 0px; border: none; background: transparent; color: #888; font-weight: bold; } "
        "QPushButton:hover { color: #333; }"
    )
    btn_close_overlay.clicked.connect(lambda: app_window.action_toggle_shortcuts.setChecked(False))
    ol_header.addWidget(btn_close_overlay)
    ol_layout.addLayout(ol_header)

    lbl = QLabel(
        "- Double-clic vide : Nouveau nœud<br>"
        "- Double-clic : Éditer le texte<br>"
        "- Maj + Entrée : Retour à la ligne<br>"
        "- Sélect + Tab : Ajouter une branche<br>"
        "- Ctrl+C / Ctrl+V : Copier/Coller<br>"
        "- Ctrl + Clic : Sélectionner 2 nœuds<br>"
        "- Suppr : Supprimer l'élément<br>"
        "- Clic droit sur couleur perso : Supprimer",
        app_window.overlay
    )
    lbl.setFont(QFont("Segoe UI", 9))
    ol_layout.addWidget(lbl)
    app_window.overlay.resize(260, 190)  # 📐 Ajusté pour laisser de la place au bouton de fermeture
    app_window.overlay.move(20, 100)

    show_overlay = app_window.settings.value("show_shortcuts_overlay", True, type=bool)
    app_window.overlay.setVisible(show_overlay)
    if hasattr(app_window, 'action_toggle_shortcuts') and app_window.action_toggle_shortcuts is not None:
        app_window.action_toggle_shortcuts.setChecked(show_overlay)
