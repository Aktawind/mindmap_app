from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QComboBox, QInputDialog
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QDate
from controllers.tools_controller import ToolsController

def create_node_toolbar(app_window) -> None:
    """
    Initialise et configure la barre d'outils contextuelle (StyleBar) 
    et l'overlay d'aide pour la fenêtre principale.
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

    # 1. Configuration de la Barre de Style Principale
    app_window.style_bar = QFrame(app_window)
    app_window.style_bar.setObjectName("StyleBar")
    app_window.style_bar.setStyleSheet("""
        #StyleBar { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }
        #StyleBar QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 12px; color: #1e293b; }
        #StyleBar QPushButton:hover { background: #e2e8f0; }
        #StyleBar QPushButton:checked { background: #cbd5e1; font-weight: bold; }
        #StyleBar QComboBox { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 4px; border-radius: 8px; min-width: 100px; color: #1e293b; }
    """)
    style_layout = QHBoxLayout(app_window.style_bar)
    style_layout.setContentsMargins(10, 5, 10, 5)
    
    # 2. Section : Contrôles des Nœuds (Node Controls)
    app_window.node_controls = QWidget(app_window.style_bar)
    nc_layout = QHBoxLayout(app_window.node_controls)
    nc_layout.setContentsMargins(0, 0, 0, 0)
    
    btn_bold = QPushButton("Bold", app_window.node_controls)
    btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    btn_bold.setFixedSize(45, 26)
    btn_bold.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_bold.clicked.connect(app_window.style_controller.toggle_bold)
    nc_layout.addWidget(btn_bold)

    btn_italic = QPushButton("Italic", app_window.node_controls)
    font_it = QFont("Arial", 10)
    font_it.setItalic(True)
    btn_italic.setFont(font_it)
    btn_italic.setFixedSize(45, 26)
    btn_italic.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_italic.clicked.connect(app_window.style_controller.toggle_italic)
    nc_layout.addWidget(btn_italic)

    btn_strike = QPushButton("Strike", app_window.node_controls)
    font_st = QFont("Arial", 10)
    font_st.setStrikeOut(True)
    btn_strike.setFont(font_st)
    btn_strike.setFixedSize(45, 26)
    btn_strike.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_strike.clicked.connect(app_window.style_controller.toggle_strikethrough)
    nc_layout.addWidget(btn_strike)
   
    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    app_window.shape_combo = QComboBox(app_window.node_controls)
    app_window.shape_combo.addItem("Rectangle", "box")
    app_window.shape_combo.addItem("Losange", "diamond")
    app_window.shape_combo.addItem("Ellipse", "ellipse")
    app_window.shape_combo.addItem("Parallélogramme", "parallelogram")
    app_window.shape_combo.currentIndexChanged.connect(app_window.style_controller.on_shape_combo_changed)
    nc_layout.addWidget(app_window.shape_combo)
    
    nc_layout.addWidget(ToolsController.create_separator(app_window))

    app_window.status_combo = QComboBox(app_window.node_controls)
    app_window.status_combo.addItem("⚪ Aucun statut", "none")
    app_window.status_combo.addItem("🚨 Urgent", "urgent")
    app_window.status_combo.addItem("⏳ En cours", "progress")
    app_window.status_combo.addItem("✅ Terminé", "done")
    app_window.status_combo.currentIndexChanged.connect(app_window.style_controller.on_status_combo_changed)
    nc_layout.addWidget(app_window.status_combo)

    nc_layout.addWidget(ToolsController.create_separator(app_window))

    # 🟢 AJOUTS PARAMÈTRES DE NOEUD : Priorité, Date & Mode Compact
    app_window.priority_combo = QComboBox(app_window.node_controls)
    app_window.priority_combo.addItem("⚪️ Priorité Normale", "none")
    app_window.priority_combo.addItem("🟡 Priorité Moyenne", "mid")
    app_window.priority_combo.addItem("🔴 Priorité Haute", "high")
    if hasattr(app_window.style_controller, 'on_priority_combo_changed'):
        app_window.priority_combo.currentIndexChanged.connect(app_window.style_controller.on_priority_combo_changed)
    nc_layout.addWidget(app_window.priority_combo)

    app_window.btn_set_date = QPushButton("📅 Échéance", app_window.node_controls)
    if hasattr(app_window.style_controller, 'prompt_node_date'):
        app_window.btn_set_date.clicked.connect(app_window.style_controller.prompt_node_date)
    nc_layout.addWidget(app_window.btn_set_date)

    app_window.btn_compact = QPushButton("🗜️ Compact", app_window.node_controls)
    app_window.btn_compact.setCheckable(True)
    if hasattr(app_window.style_controller, 'toggle_compact_mode'):
        app_window.btn_compact.clicked.connect(app_window.style_controller.toggle_compact_mode)
    nc_layout.addWidget(app_window.btn_compact)

    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    # Palette de couleurs
    colors_palette = [
        ('#60A5FA', '#3B82F6'), ('#E0F7FA', '#4DD0E1'), 
        ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'), 
        ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')
    ]
    for color, border in colors_palette:            
        btn = QPushButton(app_window.node_controls)
        btn.setFixedSize(22, 22)
        btn.setStyleSheet(f"background: {color}; border: 2px solid {border}; border-radius: 11px;")
        btn.clicked.connect(lambda _, c=color, b=border: app_window.style_controller.change_color(c, b))
        nc_layout.addWidget(btn)
        
    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    btn_attach = QPushButton("📎 Fichier", app_window.node_controls)
    btn_attach.clicked.connect(app_window.attachment_controller.attach_file)
    nc_layout.addWidget(btn_attach)
    
    btn_url = QPushButton("🔗 URL", app_window.node_controls)
    btn_url.clicked.connect(app_window.attachment_controller.attach_url)
    nc_layout.addWidget(btn_url)

    btn_img = QPushButton("🏞️ Image", app_window.node_controls)
    btn_img.clicked.connect(app_window.image_controller.attach_image_to_selected)
    nc_layout.addWidget(btn_img)

    # Petit bouton bonus pour redimensionner la hauteur de l'image du nœud
    app_window.btn_img_h = QPushButton("↕️ H-Img", app_window.node_controls)
    app_window.btn_img_h.setToolTip("Modifier la hauteur de l'image")
    app_window.btn_img_h.clicked.connect(app_window.image_controller.change_image_height)
    nc_layout.addWidget(app_window.btn_img_h)
    
    app_window.btn_open = QPushButton("📂 Ouvrir", app_window.node_controls)
    app_window.btn_open.setStyleSheet("background: #2D3748; color: white;")
    app_window.btn_open.clicked.connect(app_window.attachment_controller.open_file)
    nc_layout.addWidget(app_window.btn_open)

    app_window.btn_detach = QPushButton("❌ Dissocier", app_window.node_controls)
    app_window.btn_detach.setStyleSheet("background: #FED7D7; color: #C53030;")
    app_window.btn_detach.clicked.connect(app_window.attachment_controller.detach_links)
    nc_layout.addWidget(app_window.btn_detach)
    
    style_layout.addWidget(app_window.node_controls)
    
    # 3. Section : Contrôles des Branches (Edge Controls)
    app_window.edge_controls = QWidget(app_window.style_bar)
    ec_layout = QHBoxLayout(app_window.edge_controls)
    ec_layout.setContentsMargins(0, 0, 0, 0)
    
    btn_edit_edge = QPushButton("Texte de branche", app_window.edge_controls)
    btn_edit_edge.clicked.connect(app_window.editing_controller.edit_selected_edge)
    ec_layout.addWidget(btn_edit_edge)
    
    ec_layout.addWidget(ToolsController.create_separator(app_window))
    
    app_window.arrow_combo = QComboBox(app_window.edge_controls)
    app_window.arrow_combo.addItem("➖ Aucune flèche", "none")
    app_window.arrow_combo.addItem("➡️ Flèche Avant", "forward")
    app_window.arrow_combo.addItem("⬅️ Flèche Arrière", "backward")
    app_window.arrow_combo.addItem("↔️ Double flèche", "both")
    app_window.arrow_combo.currentIndexChanged.connect(app_window.routing_controller.on_arrow_combo_changed)
    ec_layout.addWidget(app_window.arrow_combo)
    
    style_layout.addWidget(app_window.edge_controls)
    
    # 4. Section : Liaison Inter-nœuds (Connect Controls)
    app_window.connect_controls = QWidget(app_window.style_bar)
    cc_layout = QHBoxLayout(app_window.connect_controls)
    cc_layout.setContentsMargins(0, 0, 0, 0)
    btn_connect = QPushButton("Relier les nœuds", app_window.connect_controls)
    btn_connect.setStyleSheet("background: #EBF8FF; border: 1px solid #90CDF4; color: #2B6CB0; font-weight: bold;")
    btn_connect.clicked.connect(app_window.graph_controller.connect_selected_nodes)
    cc_layout.addWidget(btn_connect)
    style_layout.addWidget(app_window.connect_controls)
    
    app_window.style_bar.hide()
    
    # 5. Overlay d'aide contextuel
    app_window.overlay = QFrame(app_window)
    app_window.overlay.setStyleSheet("background: rgba(255,255,255,0.95); border-radius: 8px; border: 1px solid #ddd; color: #2d3748;")
    ol_layout = QVBoxLayout(app_window.overlay)
    
    lbl = QLabel(
        "<b>Commandes :</b><br>"
        "- Double-clic vide : Nouveau nœud<br>"
        "- Double-clic : Éditer le texte<br>"
        "- Maj + Entrée : Retour à la ligne<br>"
        "- Sélect + Tab : Ajouter une branche<br>"
        "- Ctrl+C / Ctrl+V : Copier/Coller<br>"
        "- Ctrl + Clic : Sélectionner 2 nœuds<br>"
        "- Suppr : Supprimer l'élément", 
        app_window.overlay
    )
    lbl.setFont(QFont("Segoe UI", 9))
    ol_layout.addWidget(lbl)
    app_window.overlay.resize(230, 155)  # 📐 Ajusté à 155 pour laisser de la place au texte
    app_window.overlay.move(20, 100)