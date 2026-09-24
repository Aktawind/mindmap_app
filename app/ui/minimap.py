"""Mini-carte de navigation : aperçu réduit de la carte active dans un coin de la fenêtre,
avec le rectangle de la zone actuellement visible, cliquable/glissable pour s'y déplacer
directement. Affichable ou non depuis le menu Affichage (état mémorisé)."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QRectF, QTimer

from ui import theme

WIDTH, HEIGHT = 220, 160
MARGIN_FROM_EDGE = 20
CONTENT_PADDING = 10
SCENE_PADDING = 60


def _fit_rect(source, target):
    """Calcule le sous-rectangle de `target` qui contient `source` à l'échelle, centré,
    en conservant son ratio d'aspect (même logique que Qt.AspectRatioMode.KeepAspectRatio,
    mais explicite pour qu'on puisse réutiliser l'échelle pour les conversions de coordonnées)."""
    if source.width() <= 0 or source.height() <= 0:
        return QRectF(target), 1.0
    scale = min(target.width() / source.width(), target.height() / source.height())
    w, h = source.width() * scale, source.height() * scale
    x = target.x() + (target.width() - w) / 2
    y = target.y() + (target.height() - h) / 2
    return QRectF(x, y, w, h), scale


class MiniMapWidget(QWidget):
    def __init__(self, app_window):
        super().__init__(app_window)
        self.app_window = app_window
        self.setFixedSize(WIDTH, HEIGHT)
        self._scene_rect = None
        self._fitted_rect = None
        self._scale = 1.0
        self._dragging = False

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._on_tick)

    def set_active(self, active):
        if active:
            self.reposition()
            self.raise_()
            self._timer.start()
        else:
            self._timer.stop()
        self.setVisible(active)

    def _on_tick(self):
        if self.isVisible():
            self.update()

    def reposition(self):
        parent = self.app_window
        if parent is None:
            return
        x = parent.width() - self.width() - MARGIN_FROM_EDGE
        y = parent.height() - self.height() - MARGIN_FROM_EDGE
        self.move(max(0, x), max(0, y))

    def _current_view(self):
        ws = self.app_window.current_workspace()
        if not ws or not hasattr(ws, 'scene') or not hasattr(ws, 'view'):
            return None, None
        return ws.scene, ws.view

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = theme.get_palette(self.app_window)

        painter.fillRect(self.rect(), QColor(p['bg_elevated']))
        painter.setPen(QPen(QColor(p['border_strong']), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        scene, view = self._current_view()
        self._scene_rect = None
        if not scene or not view:
            return

        items_rect = scene.itemsBoundingRect()
        if items_rect.isEmpty():
            return
        items_rect = items_rect.adjusted(-SCENE_PADDING, -SCENE_PADDING, SCENE_PADDING, SCENE_PADDING)

        target = QRectF(self.rect().adjusted(CONTENT_PADDING, CONTENT_PADDING, -CONTENT_PADDING, -CONTENT_PADDING))
        fitted, scale = _fit_rect(items_rect, target)
        self._scene_rect, self._fitted_rect, self._scale = items_rect, fitted, scale

        scene.render(painter, fitted, items_rect, Qt.AspectRatioMode.IgnoreAspectRatio)

        visible_scene_rect = QRectF(view.mapToScene(view.viewport().rect()).boundingRect())
        top_left = self._scene_to_widget(visible_scene_rect.topLeft())
        bottom_right = self._scene_to_widget(visible_scene_rect.bottomRight())
        painter.setPen(QPen(QColor(p['accent']), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(top_left, bottom_right))

    def _scene_to_widget(self, scene_pt):
        return (self._fitted_rect.topLeft()
                + (scene_pt - self._scene_rect.topLeft()) * self._scale)

    def _widget_to_scene(self, widget_pt):
        return (self._scene_rect.topLeft()
                + (widget_pt - self._fitted_rect.topLeft()) / self._scale)

    def _navigate_to(self, widget_pos):
        if not self._scene_rect or not self._fitted_rect or self._scale <= 0:
            return
        _, view = self._current_view()
        if not view:
            return
        scene_pt = self._widget_to_scene(widget_pos)
        view.centerOn(scene_pt)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._navigate_to(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._navigate_to(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


def create_minimap(app_window):
    """Crée la mini-carte (masquée par défaut) et restaure son état affiché/masqué mémorisé."""
    app_window.minimap = MiniMapWidget(app_window)
    show = app_window.settings.value("show_minimap", False, type=bool)
    app_window.minimap.set_active(show)
    return app_window.minimap


def toggle_minimap(app_window, checked):
    app_window.settings.setValue("show_minimap", checked)
    if hasattr(app_window, 'minimap') and app_window.minimap is not None:
        app_window.minimap.set_active(checked)
