# views/toolbar.py
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolBar, QComboBox, QStyle, QWidget
from PyQt6.QtGui import QAction, QIcon
from controllers.tools_controller import ToolsController
from controllers.style_controller import StyleController
from controllers.graph_controller import GraphController
from controllers.attachment_controller import AttachmentController
from services.project_service import ProjectService

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

def create_toolbar(app_window):
    workspace_toolbar = app_window.addToolBar("workspace")
    workspace_toolbar.setMovable(False)
    workspace_toolbar.setStyleSheet("""
        QToolBar { background: #F1F5F9; border-bottom: 1px solid #CBD5E1; padding: 4px; spacing: 8px; }
        QPushButton { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
        QPushButton:hover { background: #E2E8F0; }
        QLabel { font-size: 11px; color: #475569; font-weight: bold; }
    """)

    # Label d'information sur la workspace active
    app_window.lbl_workspace_status = QLabel("📂 Espace de travail : Aucun")
    workspace_toolbar.addWidget(app_window.lbl_workspace_status)
    workspace_toolbar.addSeparator()

    btn_add_to_coll = QPushButton("➕")
    btn_add_to_coll.setToolTip("Inclure l'onglet actuel dans l'espace de travail")
    btn_remove_from_coll = QPushButton("❌")
    btn_remove_from_coll.setToolTip("Retirer l'onglet actuel de l'espace de travail")
    workspace_toolbar.addSeparator()
    workspace_toolbar.addWidget(btn_add_to_coll)
    workspace_toolbar.addWidget(btn_remove_from_coll)
    btn_add_to_coll.clicked.connect(app_window.add_current_tab_to_workspace)
    btn_remove_from_coll.clicked.connect(app_window.remove_current_tab_from_workspace)

    app_window.header_right_widget = QWidget()
    hr_layout = QHBoxLayout(app_window.header_right_widget)
    hr_layout.setContentsMargins(0, 0, 10, 0)

    btn_save = QPushButton("💾")
    btn_save.setToolTip("Sauvegarder")
    btn_save.clicked.connect(app_window.save_project) 
    workspace_toolbar.addWidget(btn_save)

    app_window.btn_snap = QPushButton(" 🧲 Aimant Grille ")
    app_window.btn_snap.setCheckable(True)
    app_window.btn_snap.setStyleSheet("""
        QPushButton { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #f1f5f9; }
        QPushButton:checked { background: #3B82F6; color: white; border-color: #2563EB; font-weight: bold; }
    """)
    app_window.btn_snap.clicked.connect(app_window.toggle_snap_to_grid)
    workspace_toolbar.addWidget(app_window.btn_snap)

    # Crée le bouton et active le mode "Toggle" (mémorisable)
    app_window.btn_toggle_routing = QPushButton("Liens courbes")
    app_window.btn_toggle_routing.setCheckable(True)
    app_window.btn_toggle_routing.setStyleSheet("""
        QPushButton { padding: 6px 15px; border: 1px solid #ccc; border-radius: 4px; background: #ffffff; font-weight: bold; }
    """)
    app_window.btn_toggle_routing.clicked.connect(app_window.toggle_line_routing)
    workspace_toolbar.addWidget(app_window.btn_toggle_routing)
    
    app_window.template_combo = QComboBox()
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
    app_window.template_combo.setStyleSheet("""
        QComboBox { border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 5px; background: white; }
    """)
    app_window.template_combo.currentIndexChanged.connect(app_window.apply_template)
    workspace_toolbar.addWidget(app_window.template_combo)
    
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
    btn_center.clicked.connect(ToolsController.auto_center_clicked)
    workspace_toolbar.addWidget(btn_center)

    app_window.add_tab_button = QPushButton("➕ Ajouter un onglet")
    app_window.add_tab_button.clicked.connect(app_window.new_project)
    app_window.tabs.setCornerWidget(app_window.add_tab_button, Qt.Corner.TopRightCorner)