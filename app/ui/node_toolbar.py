# ui/menus.py
from PyQt6.QtGui import QKeySequence
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

from controllers.tools_controller import ToolsController

def create_node_toolbar(app_window):
    app_window.style_bar = QFrame(app_window)
    app_window.style_bar.setObjectName("StyleBar") # <-- On lui donne un nom unique
    app_window.style_bar.setStyleSheet("""
        #StyleBar { background: white; border-radius: 20px; border: 1px solid #e2e8f0; }
        #StyleBar QPushButton { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 12px; }
        #StyleBar QPushButton:hover { background: #e2e8f0; }
        #StyleBar QComboBox { background: #f1f5f9; border: 1px solid #cbd5e1; padding: 4px; border-radius: 8px; min-width: 110px; }
    """)
    style_layout = QHBoxLayout(app_window.style_bar)
    
    app_window.node_controls = QWidget()
    nc_layout = QHBoxLayout(app_window.node_controls)
    nc_layout.setContentsMargins(0,0,0,0)
    
    btn_bold = QPushButton("Bold")
    btn_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    btn_bold.setFixedSize(38, 26)
    btn_bold.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
    btn_bold.clicked.connect(app_window.toggle_bold)
    nc_layout.addWidget(btn_bold)
    
    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    app_window.shape_combo = QComboBox()
    app_window.shape_combo.addItem("Rectangle", "box")
    app_window.shape_combo.addItem("Losange", "diamond")
    app_window.shape_combo.addItem("Ellipse", "ellipse")
    app_window.shape_combo.currentIndexChanged.connect(app_window.on_shape_combo_changed)
    nc_layout.addWidget(app_window.shape_combo)
    
    nc_layout.addWidget(ToolsController.create_separator(app_window))

    app_window.status_combo = QComboBox()
    app_window.status_combo.addItem("⚪ Aucun statut", "none")
    app_window.status_combo.addItem("🚨 Urgent", "urgent")
    app_window.status_combo.addItem("⏳ En cours", "progress")
    app_window.status_combo.addItem("✅ Terminé", "done")
    app_window.status_combo.currentIndexChanged.connect(app_window.on_status_combo_changed)
    nc_layout.addWidget(app_window.status_combo)

    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    for color, border in [('#60A5FA', '#3B82F6'), ('#E0F7FA', '#4DD0E1'), ('#FFF3E0', '#FFB74D'), ('#E8F5E9', '#81C784'), ('#F3E5F5', '#CE93D8'), ('#FFEBEE', '#EF9A9A')]:            
        btn = QPushButton()
        btn.setFixedSize(22, 22)
        btn.setStyleSheet(f"background: {color}; border: 2px solid {border}; border-radius: 11px;")
        btn.clicked.connect(lambda checked, c=color, b=border: app_window.change_color(c, b))
        nc_layout.addWidget(btn)
        
    nc_layout.addWidget(ToolsController.create_separator(app_window))
    
    btn_attach = QPushButton("📎 Fichier")
    btn_attach.clicked.connect(app_window.attach_file)
    nc_layout.addWidget(btn_attach)
    
    btn_url = QPushButton("🔗 URL")
    btn_url.clicked.connect(app_window.attach_url)
    nc_layout.addWidget(btn_url)
    
    app_window.btn_open = QPushButton("📂 Ouvrir")
    app_window.btn_open.setStyleSheet("background: #2D3748; color: white;")
    app_window.btn_open.clicked.connect(app_window.open_file)
    nc_layout.addWidget(app_window.btn_open)

    app_window.btn_detach = QPushButton("❌ Dissocier")
    app_window.btn_detach.setStyleSheet("background: #FED7D7; color: #C53030;")
    app_window.btn_detach.clicked.connect(app_window.detach_links)
    nc_layout.addWidget(app_window.btn_detach)
    
    style_layout.addWidget(app_window.node_controls)
    
    app_window.edge_controls = QWidget()
    ec_layout = QHBoxLayout(app_window.edge_controls)
    ec_layout.setContentsMargins(0,0,0,0)
    
    btn_edit_edge = QPushButton("Texte de branche")
    btn_edit_edge.clicked.connect(app_window.editing_controller.edit_selected_edge)
    ec_layout.addWidget(btn_edit_edge)
    
    ec_layout.addWidget(ToolsController.create_separator(app_window))
    
    app_window.arrow_combo = QComboBox()
    app_window.arrow_combo.addItem("➖ Aucune flèche", "none")
    app_window.arrow_combo.addItem("➡️ Flèche Avant", "forward")
    app_window.arrow_combo.addItem("⬅️ Flèche Arrière", "backward")
    app_window.arrow_combo.addItem("↔️ Double flèche", "both")
    app_window.arrow_combo.currentIndexChanged.connect(app_window.on_arrow_combo_changed)
    ec_layout.addWidget(app_window.arrow_combo)
    
    style_layout.addWidget(app_window.edge_controls)
    
    app_window.connect_controls = QWidget()
    cc_layout = QHBoxLayout(app_window.connect_controls)
    cc_layout.setContentsMargins(0,0,0,0)
    btn_connect = QPushButton("Relier les nœuds")
    btn_connect.setStyleSheet("background: #EBF8FF; border: 1px solid #90CDF4; color: #2B6CB0; font-weight: bold;")
    btn_connect.clicked.connect(app_window.connect_selected_nodes)
    cc_layout.addWidget(btn_connect)
    style_layout.addWidget(app_window.connect_controls)
    
    app_window.style_bar.hide()
    
    app_window.overlay = QFrame(app_window)
    app_window.overlay.setStyleSheet("background: rgba(255,255,255,0.95); border-radius: 8px; border: 1px solid #ddd;")
    ol_layout = QVBoxLayout(app_window.overlay)
    lbl = QLabel("<b>Commandes :</b><br>- Double-clic vide : Nouveau nœud<br>- Double-clic : Éditer le texte<br>- Sélect + Tab : Ajouter une branche<br>- Ctrl+C / Ctrl+V : Copier/Coller<br>- Ctrl + Clic : Sélectionner 2 nœuds<br>- Suppr : Supprimer l'élément")
    lbl.setFont(QFont("Segoe UI", 9))
    ol_layout.addWidget(lbl)
    app_window.overlay.resize(230, 140)
    app_window.overlay.move(20, 100)