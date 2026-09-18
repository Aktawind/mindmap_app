"""Dessine, derrière les nœuds d'une carte, un "canva" de fond (Kanban, matrices, etc.)
qui reste ancré aux coordonnées de la scène : il suit donc le pan/zoom comme le reste de
la carte, ce qui permet de glisser des nœuds dans des colonnes/quadrants qui restent
alignés avec eux quel que soit le niveau de zoom.

Chaque canva est aussi sensible au thème (clair/sombre) et à une échelle (`canvas_scale`)
qui agrandit réellement la zone de dessin (pas un simple dézoom) pour loger plus de nœuds.
"""
import math
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainterPath

# Zone de scène (en unités de coordonnées de la carte) sur laquelle chaque canva est dessiné,
# avant application de l'échelle (`canvas_scale`) choisie par l'utilisateur.
CANVAS_RECT = QRectF(-500, -350, 1000, 700)

CANVAS_TYPES = {
    "none": "Feuille blanche",
    "kanban": "Tableau Kanban",
    "eisenhower": "Matrice d'Eisenhower",
    "swot": "Matrice SWOT",
    "timeline": "Frise chronologique",
    "ikigai": "Cercles de Ikigai",
    #"roue": "Graph circulaire Roue de la Vie (8 secteurs)",
    "pyramide": "Pyramide",
    "ishikawa": "Diagramme d'Ishikawa",
    #"moodboard": "Moodboard",
    "custom": "Image personnalisée...",
}

_LABEL_COLOR = QColor("#64748B")
_LINE_COLOR = QColor("#CBD5E1")
_LABEL_COLOR_DARK = QColor("#94A3B8")
_LINE_COLOR_DARK = QColor("#475569")


def _colors(dark):
    return (_LABEL_COLOR_DARK, _LINE_COLOR_DARK) if dark else (_LABEL_COLOR, _LINE_COLOR)


def _adapt_fill(color, dark):
    """Assombrit une couleur pastel pour le mode sombre en conservant sa teinte, pour que les
    remplissages restent lisibles sur fond sombre au lieu de rester criards ou trop clairs."""
    if not dark:
        return color
    h, s, l, a = color.getHslF()
    return QColor.fromHslF(h, min(1.0, s * 0.9), max(0.16, l * 0.35), a)


def _font(size=13, bold=False, scale=1.0):
    f = QFont("Segoe UI", max(6, round(size * scale)))
    f.setBold(bold)
    return f


def draw_canvas_background(painter, canvas_type, image_path=None, image_cache=None, dark=False, scale=1.0):
    """Point d'entrée : dessine le canva sélectionné, dans les coordonnées de la scène."""
    if not canvas_type or canvas_type == "none":
        return

    scale = max(0.1, scale or 1.0)
    rect = QRectF(
        CANVAS_RECT.x() * scale, CANVAS_RECT.y() * scale,
        CANVAS_RECT.width() * scale, CANVAS_RECT.height() * scale
    )

    painter.save()
    try:
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        if canvas_type == "custom":
            _draw_custom_image(painter, image_path, image_cache, rect)
        else:
            drawer = _DRAWERS.get(canvas_type)
            if drawer:
                drawer(painter, rect, dark, scale)
    finally:
        painter.restore()


def _draw_custom_image(painter, image_path, image_cache, rect):
    if not image_path:
        return

    pixmap = None
    if image_cache is not None:
        pixmap = image_cache.get(image_path)
        if pixmap is None:
            pixmap = QPixmap(image_path)
            image_cache[image_path] = pixmap
    else:
        pixmap = QPixmap(image_path)

    if pixmap.isNull():
        return

    scaled = pixmap.scaled(
        int(rect.width()), int(rect.height()),
        Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    x = rect.center().x() - scaled.width() / 2
    y = rect.center().y() - scaled.height() / 2
    painter.drawPixmap(int(x), int(y), scaled)


def _draw_kanban(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    columns = ["📋 À faire", "🔧 En cours", "✅ Terminé"]
    col_width = rect.width() / len(columns)

    painter.setFont(_font(15, bold=True, scale=scale))
    for i, title in enumerate(columns):
        x = rect.left() + i * col_width
        col_rect = QRectF(x, rect.top(), col_width, rect.height())

        painter.setPen(QPen(line_color, 2))
        painter.setBrush(QBrush(_adapt_fill(QColor(255, 255, 255, 60), dark)))
        painter.drawRect(col_rect)

        header_rect = QRectF(col_rect.left(), col_rect.top(), col_rect.width(), 40)
        painter.setBrush(QBrush(_adapt_fill(QColor("#E2E8F0"), dark)))
        painter.drawRect(header_rect)
        painter.setPen(QPen(label_color))
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, title)


def _draw_eisenhower(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    cx, cy = rect.center().x(), rect.center().y()

    painter.setPen(QPen(line_color, 2))
    painter.drawRect(rect)
    painter.drawLine(QPointF(cx, rect.top()), QPointF(cx, rect.bottom()))
    painter.drawLine(QPointF(rect.left(), cy), QPointF(rect.right(), cy))

    quadrants = [
        (QRectF(rect.left(), rect.top(), rect.width()/2, rect.height()/2), "🔥 Urgent & Important\n(Faire)"),
        (QRectF(cx, rect.top(), rect.width()/2, rect.height()/2), "🎯 Important, pas urgent\n(Planifier)"),
        (QRectF(rect.left(), cy, rect.width()/2, rect.height()/2), "⚡ Urgent, pas important\n(Déléguer)"),
        (QRectF(cx, cy, rect.width()/2, rect.height()/2), "🗑️ Ni urgent ni important\n(Éliminer)"),
    ]
    painter.setFont(_font(13, bold=True, scale=scale))
    painter.setPen(QPen(label_color))
    for q_rect, label in quadrants:
        painter.drawText(q_rect.adjusted(12, 12, -12, -12),
                          Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)

    painter.setFont(_font(11, scale=scale))
    painter.drawText(QRectF(rect.left(), rect.top() - 26, rect.width(), 20),
                      Qt.AlignmentFlag.AlignCenter, "URGENCE →")
    painter.save()
    painter.translate(rect.left() - 26, cy)
    painter.rotate(-90)
    painter.drawText(QRectF(-rect.height()/2, -10, rect.height(), 20),
                      Qt.AlignmentFlag.AlignCenter, "IMPORTANCE →")
    painter.restore()


def _draw_swot(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    cx, cy = rect.center().x(), rect.center().y()
    quadrants = [
        (QRectF(rect.left(), rect.top(), rect.width()/2, rect.height()/2), "💪 FORCES", QColor(220, 252, 231, 130)),
        (QRectF(cx, rect.top(), rect.width()/2, rect.height()/2), "⚠️ FAIBLESSES", QColor(254, 226, 226, 130)),
        (QRectF(rect.left(), cy, rect.width()/2, rect.height()/2), "🚀 OPPORTUNITÉS", QColor(219, 234, 254, 130)),
        (QRectF(cx, cy, rect.width()/2, rect.height()/2), "🛑 MENACES", QColor(254, 243, 199, 130)),
    ]
    painter.setFont(_font(15, bold=True, scale=scale))
    for q_rect, label, color in quadrants:
        painter.setPen(QPen(line_color, 2))
        painter.setBrush(QBrush(_adapt_fill(color, dark)))
        painter.drawRect(q_rect)
        painter.setPen(QPen(label_color))
        painter.drawText(QRectF(q_rect.left() + 12, q_rect.top() + 8, q_rect.width() - 24, 30),
                          Qt.AlignmentFlag.AlignLeft, label)


def _draw_timeline(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    y = rect.center().y()
    painter.setFont(_font(13, bold=True, scale=scale))
    painter.setPen(QPen(label_color))
    painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), 30),
                      Qt.AlignmentFlag.AlignCenter, "🕐 Frise chronologique")

    line_left = rect.left() + 60
    line_right = rect.right() - 60
    painter.setPen(QPen(line_color, 3))
    painter.drawLine(QPointF(line_left, y), QPointF(line_right, y))

    steps = 6
    painter.setFont(_font(11, scale=scale))
    for i in range(steps + 1):
        x = line_left + ((line_right - line_left) / steps) * i
        painter.setPen(QPen(line_color, 2))
        painter.drawLine(QPointF(x, y - 12), QPointF(x, y + 12))
        painter.setPen(QPen(label_color))
        painter.drawText(QRectF(x - 60, y + 16, 120, 20), Qt.AlignmentFlag.AlignCenter, f"Étape {i + 1}")


def _draw_ikigai(painter, rect, dark, scale):
    label_color, _line_color = _colors(dark)
    r = min(rect.width(), rect.height()) * 0.33
    cx, cy = rect.center().x(), rect.center().y()
    offset = r * 0.55

    circles = [
        (QPointF(cx - offset, cy - offset), QColor(254, 202, 202, 100), "Ce que vous\nAIMEZ"),
        (QPointF(cx + offset, cy - offset), QColor(191, 219, 254, 100), "Ce pour quoi\nvous êtes DOUÉ"),
        (QPointF(cx - offset, cy + offset), QColor(254, 240, 138, 100), "Ce dont le\nMONDE a besoin"),
        (QPointF(cx + offset, cy + offset), QColor(187, 247, 208, 100), "Ce pour quoi\nvous êtes PAYÉ"),
    ]

    for center, color, _label in circles:
        adapted = _adapt_fill(color, dark)
        painter.setPen(QPen(adapted.darker(150), 2))
        painter.setBrush(QBrush(adapted))
        painter.drawEllipse(center, r, r)

    painter.setFont(_font(11, bold=True, scale=scale))
    painter.setPen(QPen(label_color))
    label_offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for (center, _color, label), (dx, dy) in zip(circles, label_offsets):
        text_rect = QRectF(center.x() - 70 + dx * 25, center.y() - 15 + dy * 35, 140, 40)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

    painter.setFont(_font(16, bold=True, scale=scale))
    painter.drawText(QRectF(cx - 60, cy - 15, 120, 30), Qt.AlignmentFlag.AlignCenter, "IKIGAI")


def _draw_roue(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    sectors = ["Carrière", "Finances", "Santé", "Famille", "Amis", "Loisirs", "Dév. perso", "Amour"]
    cx, cy = rect.center().x(), rect.center().y()
    radius = min(rect.width(), rect.height()) * 0.42
    n = len(sectors)
    colors = [QColor(c) for c in ["#FCA5A5", "#FDBA74", "#FDE68A", "#BEF264",
                                   "#86EFAC", "#67E8F9", "#93C5FD", "#C4B5FD"]]

    for i, (label, color) in enumerate(zip(sectors, colors)):
        start_angle = int((360 / n) * i * 16)
        span_angle = int((360 / n) * 16)
        adapted = _adapt_fill(QColor(color.red(), color.green(), color.blue(), 90), dark)
        painter.setPen(QPen(QColor(255, 255, 255) if not dark else QColor(30, 41, 59), 1))
        painter.setBrush(QBrush(adapted))
        wedge_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawPie(wedge_rect, start_angle, span_angle)

    for level in range(1, 5):
        painter.setPen(QPen(line_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius * level / 4, radius * level / 4)

    painter.setPen(QPen(line_color, 2))
    for i in range(n):
        angle = math.radians((360 / n) * i - 90)
        painter.drawLine(QPointF(cx, cy), QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    painter.setFont(_font(11, bold=True, scale=scale))
    painter.setPen(QPen(label_color))
    for i, label in enumerate(sectors):
        mid_angle = math.radians((360 / n) * i + (360 / n) / 2 - 90)
        label_r = radius + 30
        lx = cx + label_r * math.cos(mid_angle)
        ly = cy + label_r * math.sin(mid_angle)
        painter.drawText(QRectF(lx - 50, ly - 10, 100, 20), Qt.AlignmentFlag.AlignCenter, label)


def _draw_pyramide(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    levels = [
        ("Vision", QColor(191, 219, 254, 150)),
        ("Stratégie", QColor(196, 236, 226, 150)),
        ("Objectifs", QColor(254, 240, 138, 150)),
        ("Actions", QColor(254, 202, 202, 150)),
    ]
    n = len(levels)
    top_y = rect.top() + 20
    base_y = rect.bottom() - 20
    base_half_width = rect.width() * 0.4
    level_height = (base_y - top_y) / n
    cx = rect.center().x()

    painter.setFont(_font(13, bold=True, scale=scale))
    for i, (label, color) in enumerate(levels):
        y_top = top_y + i * level_height
        y_bottom = top_y + (i + 1) * level_height
        half_w_top = base_half_width * (y_top - top_y) / (base_y - top_y)
        half_w_bottom = base_half_width * (y_bottom - top_y) / (base_y - top_y)

        path = QPainterPath()
        path.moveTo(cx - half_w_top, y_top)
        path.lineTo(cx + half_w_top, y_top)
        path.lineTo(cx + half_w_bottom, y_bottom)
        path.lineTo(cx - half_w_bottom, y_bottom)
        path.closeSubpath()

        painter.setPen(QPen(line_color, 2))
        painter.setBrush(QBrush(_adapt_fill(color, dark)))
        painter.drawPath(path)

        painter.setPen(QPen(label_color))
        painter.drawText(QRectF(cx - 100, (y_top + y_bottom) / 2 - 10, 200, 20),
                          Qt.AlignmentFlag.AlignCenter, label)


def _draw_ishikawa(painter, rect, dark, scale):
    label_color, line_color = _colors(dark)
    y = rect.center().y()
    spine_left = rect.left() + 40
    spine_right = rect.right() - 130

    painter.setPen(QPen(line_color, 3))
    painter.drawLine(QPointF(spine_left, y), QPointF(spine_right, y))

    head_rect = QRectF(spine_right, y - 30, 120, 60)
    painter.setPen(QPen(line_color, 2))
    painter.setBrush(QBrush(_adapt_fill(QColor(254, 226, 226, 160), dark)))
    painter.drawRect(head_rect)
    painter.setFont(_font(12, bold=True, scale=scale))
    painter.setPen(QPen(label_color))
    painter.drawText(head_rect, Qt.AlignmentFlag.AlignCenter, "Problème /\nEffet")

    categories = ["Méthode", "Main d'œuvre", "Matériel", "Milieu", "Matière", "Mesure"]
    n = len(categories)
    span = spine_right - spine_left - 40
    columns = max(1, (n + 1) // 2)

    for i, cat in enumerate(categories):
        above = i % 2 == 0
        col = i // 2
        x = spine_left + 40 + span * (col / columns)
        bone_y = y - 80 if above else y + 80

        painter.setPen(QPen(line_color, 2))
        painter.drawLine(QPointF(x, y), QPointF(x + (30 if above else -30), bone_y))

        painter.setFont(_font(11, bold=True, scale=scale))
        painter.setPen(QPen(label_color))
        label_rect = QRectF(x - 40, (bone_y - 25) if above else (bone_y + 5), 120, 20)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, cat)


def _draw_moodboard(painter, rect, dark, scale):
    border_color = QColor("#475569") if dark else QColor("#D6D3D1")
    text_color = QColor("#94A3B8") if dark else QColor("#A8A29E")
    painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))
    painter.setBrush(QBrush(_adapt_fill(QColor(250, 250, 249, 100), dark)))
    painter.drawRoundedRect(rect, 16, 16)

    painter.setFont(_font(16, bold=True, scale=scale))
    painter.setPen(QPen(text_color))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎨 Moodboard\n(glissez vos idées ici)")


_DRAWERS = {
    "kanban": _draw_kanban,
    "eisenhower": _draw_eisenhower,
    "swot": _draw_swot,
    "timeline": _draw_timeline,
    "ikigai": _draw_ikigai,
    "roue": _draw_roue,
    "pyramide": _draw_pyramide,
    "ishikawa": _draw_ishikawa,
    "moodboard": _draw_moodboard,
}
