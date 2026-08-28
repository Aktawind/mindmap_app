import copy
import math
import os
import re

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from graphics.items import BRANCH_PALETTES
from graphics.scene import MindMapWorkspace

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
LIST_ITEM_RE = re.compile(r'^(\s*)(?:[-*+]|\d+\.)\s+(.*)$')

_INLINE_CODE_RE = re.compile(r'`([^`]*)`')
_INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_INLINE_BOLD_RE = re.compile(r'(\*\*|__)(.*?)\1')
_INLINE_ITALIC_STAR_RE = re.compile(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)')
_INLINE_ITALIC_UNDERSCORE_RE = re.compile(r'(?<!_)_(?!_)([^_]+)_(?!_)')


def _clean_inline_markdown(text):
    """Retire la syntaxe Markdown inline (gras, italique, code, liens) pour ne garder que le texte lisible."""
    text = _INLINE_CODE_RE.sub(r'\1', text)
    text = _INLINE_LINK_RE.sub(r'\1', text)
    text = _INLINE_BOLD_RE.sub(r'\2', text)
    text = _INLINE_ITALIC_STAR_RE.sub(r'\1', text)
    text = _INLINE_ITALIC_UNDERSCORE_RE.sub(r'\1', text)
    return text.strip()


class ImportController:
    def __init__(self, app):
        self.app = app

    def import_markdown(self):
        """Crée une nouvelle mindmap à partir des titres et listes d'un fichier Markdown,
        avec placement automatique des nœuds (disposition radiale) et colorisation par branche."""
        path, _ = QFileDialog.getOpenFileName(
            self.app, "Importer depuis Markdown", "", "Markdown (*.md *.markdown *.txt)"
        )
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur de lecture", f"Impossible de lire le fichier :\n{e}")
            return

        top_level = self._parse_outline(text)
        if not top_level:
            QMessageBox.warning(
                self.app, "Import impossible",
                "Aucun titre (#) ni élément de liste (-, *, 1.) n'a été trouvé dans ce fichier Markdown."
            )
            return

        file_basename = os.path.splitext(os.path.basename(path))[0]
        root_outline = top_level[0] if len(top_level) == 1 else {"text": file_basename, "children": top_level}

        root_styled = self._style_tree(root_outline)
        self._layout_radial(root_styled)

        state = {
            "root": root_styled,
            "orphan_nodes": [],
            "cross_links": [],
            "global_line_routing": "curved",
            "snap_to_grid": False,
        }

        ws = MindMapWorkspace(self.app)
        self.app.tabs.addTab(ws, file_basename)
        self.app.tabs.setCurrentWidget(ws)

        if hasattr(self.app, 'routing_controller'):
            self.app.routing_controller.update_routing_button_ui()

        self.app.serializer.apply_state(state)

        if hasattr(ws, 'undo_stack'):
            ws.undo_stack.append(copy.deepcopy(state))

        ws.is_dirty = True
        if hasattr(self.app, 'tabs_controller'):
            self.app.tabs_controller.update_title()
        if hasattr(self.app, 'workspace_controller'):
            self.app.workspace_controller.center_on_graph()

    def _parse_outline(self, text):
        """Construit une arborescence {text, children} à partir des titres (#...) et des listes
        (-, *, + ou numérotées) d'un document Markdown. Les autres lignes (paragraphes) sont ignorées."""
        root_items = []
        heading_stack = []   # [(level, node)]
        list_stack = []      # [(indent_width, node)]
        current_heading_node = None

        for raw_line in text.splitlines():
            line = raw_line.replace('\t', '    ')
            if not line.strip():
                continue

            m = HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                node = {"text": _clean_inline_markdown(m.group(2)), "children": []}

                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()

                if heading_stack:
                    heading_stack[-1][1]["children"].append(node)
                else:
                    root_items.append(node)

                heading_stack.append((level, node))
                current_heading_node = node
                list_stack = []
                continue

            m = LIST_ITEM_RE.match(line)
            if m:
                indent = len(m.group(1))
                node = {"text": _clean_inline_markdown(m.group(2)), "children": []}

                while list_stack and list_stack[-1][0] >= indent:
                    list_stack.pop()

                if list_stack:
                    list_stack[-1][1]["children"].append(node)
                elif current_heading_node:
                    current_heading_node["children"].append(node)
                else:
                    root_items.append(node)

                list_stack.append((indent, node))

        return root_items

    def _style_tree(self, outline_node, node_id="root", bg='#60A5FA', border='#3B82F6',
                     font_color='#ffffff', edge_color=None, palette_children=True):
        """Convertit récursivement l'arborescence brute en dictionnaire compatible avec
        MindMapSerializer.apply_state, en coloriant chaque branche issue de la racine
        avec une couleur distincte de BRANCH_PALETTES (héritée ensuite par ses descendants)."""
        styled = {
            "id": node_id, "label": outline_node["text"] or "(Sans titre)", "x": 0, "y": 0, "shape": "box",
            "bg": bg, "border": border, "font_color": font_color, "border_width": 1,
            "is_bold": False, "is_italic": False, "is_strikethrough": False,
            "status": "none", "attachments": [], "url_link": None,
            "image_path": None, "image_height": 150, "date": None,
            "priority": "none", "is_compact": False, "notes": "", "node_format": "default",
            "edge_color": edge_color, "edge_label": "", "edge_arrow_dir": "none",
            "children": [],
        }

        for i, child in enumerate(outline_node.get("children", [])):
            child_id = f"md_node_{id(child)}_{i}"
            if palette_children:
                pal = BRANCH_PALETTES[i % len(BRANCH_PALETTES)]
                child_styled = self._style_tree(child, child_id, pal['bg'], pal['border'], pal['text'], pal['edge'],
                                                 palette_children=False)
            else:
                child_styled = self._style_tree(child, child_id, bg, border, font_color, edge_color,
                                                 palette_children=False)
            styled["children"].append(child_styled)

        return styled

    def _count_leaves(self, node):
        children = node.get("children", [])
        if not children:
            return 1
        return sum(self._count_leaves(c) for c in children)

    def _layout_radial(self, root, radius_step=260):
        """Positionne les nœuds sur des anneaux concentriques (un par profondeur), en répartissant
        l'angle de chaque sous-arbre proportionnellement à son nombre de feuilles pour limiter les
        chevauchements sur les arborescences déséquilibrées."""
        root["x"], root["y"] = 0.0, 0.0
        self._layout_children(root, 0.0, 0.0, 0.0, 2 * math.pi, 1, radius_step)

    def _layout_children(self, node, cx, cy, angle_start, angle_end, depth, radius_step):
        children = node.get("children", [])
        if not children:
            return

        total_leaves = sum(max(self._count_leaves(c), 1) for c in children)
        span = angle_end - angle_start
        current_angle = angle_start
        radius = radius_step * depth

        for child in children:
            leaves = max(self._count_leaves(child), 1)
            child_span = span * (leaves / total_leaves)
            mid_angle = current_angle + child_span / 2
            child["x"] = cx + radius * math.cos(mid_angle)
            child["y"] = cy + radius * math.sin(mid_angle)
            self._layout_children(child, cx, cy, current_angle, current_angle + child_span, depth + 1, radius_step)
            current_angle += child_span
