"""Palette et feuilles de style pour les thèmes clair/sombre de l'application.

Le thème choisi est persisté dans les préférences (QSettings) et relu à chaque
démarrage. `apply_theme()` réapplique la feuille de style globale ainsi que
celles des widgets stylés individuellement (toolbar, panneau de propriétés,
overlay d'aide) — les éléments dessinés à la main (scène, canevas de fond,
libellés de branche) relisent le thème courant à chaque peinture via
`get_palette_for_scene()` / `is_dark_mode()`, donc ils suivent automatiquement.
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor

LIGHT = {
    "bg": "#F8FAFC",
    "bg_elevated": "#FFFFFF",
    "bg_toolbar": "#F1F5F9",
    "bg_panel": "#FFFFFF",
    "bg_input": "#FFFFFF",
    "bg_hover": "#E2E8F0",
    "border": "#CBD5E1",
    "border_strong": "#94A3B8",
    "text": "#1E293B",
    "text_muted": "#64748B",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "scene_bg": "#F8F9FA",
    "canvas_line": "#CBD5E1",
    "canvas_label": "#64748B",
    "edge_label_bg": (248, 249, 250, 230),
    "edge_label_text": "#4A5568",
    "info_bg": "#EBF8FF",
    "info_border": "#90CDF4",
    "info_text": "#2B6CB0",
    "danger_bg": "#FED7D7",
    "danger_text": "#C53030",
    "overlay_bg": "rgba(255,255,255,0.95)",
    "overlay_border": "#DDDDDD",
    "overlay_text": "#2D3748",
}

DARK = {
    "bg": "#0F172A",
    "bg_elevated": "#1E293B",
    "bg_toolbar": "#1E293B",
    "bg_panel": "#1E293B",
    "bg_input": "#334155",
    "bg_hover": "#334155",
    "border": "#334155",
    "border_strong": "#475569",
    "text": "#E2E8F0",
    "text_muted": "#94A3B8",
    "accent": "#3B82F6",
    "accent_hover": "#60A5FA",
    "scene_bg": "#111827",
    "canvas_line": "#475569",
    "canvas_label": "#94A3B8",
    "edge_label_bg": (30, 41, 59, 235),
    "edge_label_text": "#E2E8F0",
    "info_bg": "#1E3A5F",
    "info_border": "#2C5282",
    "info_text": "#90CDF4",
    "danger_bg": "#4C1D1D",
    "danger_text": "#FEB2B2",
    "overlay_bg": "rgba(30,41,59,0.95)",
    "overlay_border": "#334155",
    "overlay_text": "#E2E8F0",
}


def is_dark_mode(app_window) -> bool:
    settings = getattr(app_window, 'settings', None) if app_window else None
    if settings is None:
        return False
    return settings.value("dark_mode", False, type=bool)


def set_dark_mode(app_window, enabled: bool):
    if hasattr(app_window, 'settings'):
        app_window.settings.setValue("dark_mode", enabled)


def get_palette(app_window):
    return DARK if is_dark_mode(app_window) else LIGHT


def adapt_fill(color, dark):
    """Assombrit une couleur pastel pour le mode sombre en conservant sa teinte, pour que les
    remplissages (canevas de fond, couleurs de base des nœuds...) restent lisibles sur fond
    sombre au lieu de rester criards ou trop clairs. Sans effet en thème clair."""
    c = QColor(color)
    if not dark:
        return c
    h, s, l, a = c.getHslF()
    return QColor.fromHslF(h, min(1.0, s * 0.9), max(0.16, l * 0.35), a)


def _app_window_for_scene(scene):
    ws = getattr(scene, 'parent_workspace', None) if scene is not None else None
    return getattr(ws, 'main_app', None) if ws is not None else None


def get_palette_for_scene(scene):
    """Retrouve le thème courant à partir d'une scène (via son workspace/app parent), pour
    que les éléments dessinés à la main (canevas, libellés de branche) restent synchronisés
    avec le thème sans avoir besoin d'être notifiés explicitement à chaque changement."""
    return get_palette(_app_window_for_scene(scene))


def is_dark_mode_for_scene(scene):
    """Même principe que get_palette_for_scene(), mais renvoie directement le booléen —
    pratique pour les items (nœuds, canevas...) qui n'ont besoin que d'assombrir leurs
    propres couleurs via adapt_fill() plutôt que de lire toute la palette."""
    return is_dark_mode(_app_window_for_scene(scene))


def app_stylesheet(p):
    return f"""
        QMainWindow {{ background: {p['bg']}; }}
        QWidget {{ color: {p['text']}; }}
        QMenuBar {{ background: {p['bg_elevated']}; color: {p['text']}; border-bottom: 1px solid {p['border']}; }}
        QMenuBar::item {{ background: transparent; padding: 4px 10px; }}
        QMenuBar::item:selected {{ background: {p['bg_hover']}; }}
        QMenu {{ background: {p['bg_elevated']}; color: {p['text']}; border: 1px solid {p['border']}; }}
        QMenu::item:selected {{ background: {p['accent']}; color: white; }}
        QMenu::separator {{ background: {p['border']}; height: 1px; margin: 4px 8px; }}
        QToolTip {{ background: {p['bg_elevated']}; color: {p['text']}; border: 1px solid {p['border']}; }}
        QMessageBox, QDialog {{ background: {p['bg_elevated']}; color: {p['text']}; }}
        QLabel {{ color: {p['text']}; background: transparent; }}
        QScrollArea {{ background: {p['bg']}; border: none; }}
        QDockWidget {{ background: {p['bg']}; color: {p['text']}; }}
        QDockWidget::title {{ background: {p['bg_toolbar']}; padding: 6px; }}
        QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QSpinBox {{
            background: {p['bg_input']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 4px;
        }}
        QListWidget {{ background: {p['bg_elevated']}; color: {p['text']}; border: 1px solid {p['border']}; }}
        QCalendarWidget {{ background: {p['bg_elevated']}; color: {p['text']}; }}
        QScrollBar:vertical, QScrollBar:horizontal {{ background: {p['bg']}; }}
        QTabWidget::pane {{ border: 1px solid {p['border']}; background: {p['bg']}; }}
        QTabBar::tab {{ background: {p['bg_toolbar']}; color: {p['text']}; padding: 6px 12px; border: 1px solid {p['border']}; }}
        QTabBar::tab:selected {{ background: {p['bg_elevated']}; font-weight: bold; }}
        QPushButton {{ background: {p['bg_elevated']}; border: 1px solid {p['border']}; border-radius: 4px; padding: 4px 8px; color: {p['text']}; }}
        QPushButton:hover {{ background: {p['bg_hover']}; }}
        QComboBox {{ background: {p['bg_input']}; border: 1px solid {p['border']}; border-radius: 4px; padding: 4px 6px; color: {p['text']}; }}
        QComboBox QAbstractItemView {{ background: {p['bg_elevated']}; color: {p['text']}; selection-background-color: {p['accent']}; }}
        QToolButton#SectionToggle {{ border: none; font-weight: bold; padding: 6px 2px; text-align: left; color: {p['text']}; background: transparent; }}
        QToolButton#SectionToggle:hover {{ background: {p['bg_hover']}; border-radius: 4px; }}
    """


def toolbar_stylesheet(p):
    return f"""
        QToolBar {{ background: {p['bg_toolbar']}; border-bottom: 1px solid {p['border']}; padding: 4px; spacing: 8px; }}
        QPushButton {{ background: {p['bg_elevated']}; border: 1px solid {p['border']}; border-radius: 4px; padding: 4px 8px; font-size: 12px; color: {p['text']}; }}
        QPushButton:hover {{ background: {p['bg_hover']}; }}
        QLabel {{ font-size: 11px; color: {p['text_muted']}; font-weight: bold; }}
        QComboBox {{ border: 1px solid {p['border']}; border-radius: 4px; padding: 4px 6px; background: {p['bg_input']}; color: {p['text']}; font-size: 12px; min-width: 100px; }}
        QComboBox:hover {{ border-color: {p['border_strong']}; }}
        QComboBox QAbstractItemView {{ background: {p['bg_elevated']}; color: {p['text']}; selection-background-color: {p['accent']}; }}
    """


def panel_stylesheet(p):
    return f"""
        QWidget#PropertiesPanel {{ background: {p['bg_panel']}; }}
        QPushButton {{ background: {p['bg_input']}; border: 1px solid {p['border']}; padding: 6px 10px; border-radius: 8px; color: {p['text']}; }}
        QPushButton:hover {{ background: {p['bg_hover']}; }}
        QPushButton:checked {{ background: {p['border_strong']}; font-weight: bold; }}
        QComboBox {{ background: {p['bg_input']}; border: 1px solid {p['border']}; padding: 4px; border-radius: 8px; color: {p['text']}; }}
        QComboBox QAbstractItemView {{ background: {p['bg_elevated']}; color: {p['text']}; selection-background-color: {p['accent']}; }}
    """


def overlay_stylesheet(p):
    return f"background: {p['overlay_bg']}; border-radius: 8px; border: 1px solid {p['overlay_border']}; color: {p['overlay_text']};"


def connect_button_stylesheet(p):
    return f"background: {p['info_bg']}; border: 1px solid {p['info_border']}; color: {p['info_text']}; font-weight: bold;"


def danger_button_stylesheet(p):
    return f"background: {p['danger_bg']}; color: {p['danger_text']};"


def toggle_button_stylesheet(p):
    return f"""
        QPushButton {{ padding: 5px 10px; border: 1px solid {p['border']}; border-radius: 4px; background: {p['bg_toolbar']}; color: {p['text']}; }}
        QPushButton:checked {{ background: {p['accent']}; color: white; border-color: {p['accent_hover']}; font-weight: bold; }}
    """


def apply_theme(app_window):
    """Réapplique le thème courant à l'ensemble de l'interface (à appeler à l'initialisation
    et à chaque bascule clair/sombre)."""
    p = get_palette(app_window)

    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(app_stylesheet(p))

    if getattr(app_window, 'workspace_toolbar', None) is not None:
        app_window.workspace_toolbar.setStyleSheet(toolbar_stylesheet(p))

    if getattr(app_window, 'properties_panel', None) is not None:
        app_window.properties_panel.setStyleSheet(panel_stylesheet(p))

    if getattr(app_window, 'overlay', None) is not None:
        app_window.overlay.setStyleSheet(overlay_stylesheet(p))

    if getattr(app_window, 'btn_connect_nodes', None) is not None:
        app_window.btn_connect_nodes.setStyleSheet(connect_button_stylesheet(p))

    if getattr(app_window, 'btn_detach', None) is not None:
        app_window.btn_detach.setStyleSheet(danger_button_stylesheet(p))

    if getattr(app_window, 'btn_snap', None) is not None:
        app_window.btn_snap.setStyleSheet(toggle_button_stylesheet(p))

    if callable(getattr(app_window, 'refresh_preset_colors', None)):
        app_window.refresh_preset_colors()

    # Repeint immédiatement toutes les scènes ouvertes (fond + canevas) avec le nouveau thème
    if hasattr(app_window, 'tabs') and app_window.tabs is not None:
        for i in range(app_window.tabs.count()):
            ws = app_window.tabs.widget(i)
            if ws is not None and hasattr(ws, 'scene') and ws.scene is not None:
                ws.scene.update()
