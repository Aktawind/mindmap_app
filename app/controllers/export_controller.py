import os
from PyQt6.QtCore import QMarginsF, QRectF
from PyQt6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QPixmap
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtPrintSupport import QPrinter

from graphics.items import NodeItem

class ExportController:
    def __init__(self, app):
        self.app = app

    def _get_default_filename(self, ws, extension):
        """Génère un nom de fichier par défaut basé sur le projet actuel."""
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            return f"{base}.{extension}"
        return f"ma_mindmap.{extension}"

    def export_png(self):
        """Exporte l'arborescence graphique visible en image haute définition PNG."""
        ws = self.app.current_workspace()
        if not ws: return
        
        rect = ws.scene.itemsBoundingRect()
        if rect.isEmpty() or rect.width() <= 0 or rect.height() <= 0:
            QMessageBox.warning(self.app, "Export impossible", "La carte mentale est vide.")
            return

        rect = rect.adjusted(-50, -50, 50, 50)
        default_name = self._get_default_filename(ws, "png")
        
        path, _ = QFileDialog.getSaveFileName(self.app, "Exporter PNG", default_name, "PNG (*.png)")
        if not path: return
        
        ws.scene.clearSelection()
        ratio = self.app.devicePixelRatioF() if hasattr(self.app, 'devicePixelRatioF') else self.app.devicePixelRatio()
        
        pixmap = QPixmap(int(rect.width() * ratio), int(rect.height() * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(QColor('#f8f9fa'))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        painter.scale(ratio, ratio)
        target_rect = QRectF(0, 0, rect.width(), rect.height())
        
        ws.scene.render(painter, target=target_rect, source=rect)
        painter.end()
        
        if not pixmap.save(path, "PNG", 100):
            QMessageBox.critical(self.app, "Erreur", "Impossible d'enregistrer l'image sur le disque.")

    def export_pdf(self):
        """Exporte la carte au format PDF vectoriel ajusté sur une feuille A4."""
        ws = self.app.current_workspace()
        if not ws: return
        
        rect = ws.scene.itemsBoundingRect()
        if rect.isEmpty() or rect.width() <= 0 or rect.height() <= 0:
            QMessageBox.warning(self.app, "Export impossible", "La carte mentale est vide.")
            return

        rect = rect.adjusted(-40, -40, 40, 40)
        default_name = self._get_default_filename(ws, "pdf")
            
        path, _ = QFileDialog.getSaveFileName(self.app, "Exporter PDF Vectoriel", default_name, "PDF (*.pdf)")
        if not path: return
        
        ws.scene.clearSelection()
        
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        
        layout = QPageLayout()
        if rect.width() > rect.height():
            layout.setOrientation(QPageLayout.Orientation.Landscape)
        else:
            layout.setOrientation(QPageLayout.Orientation.Portrait)
            
        layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        layout.setMargins(QMarginsF(10, 10, 10, 10))
        printer.setPageLayout(layout)
            
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        
        scale_x = page_rect.width() / rect.width()
        scale_y = page_rect.height() / rect.height()
        scale = min(scale_x, scale_y)
        
        target_w = rect.width() * scale
        target_h = rect.height() * scale
        target_x = page_rect.left() + (page_rect.width() - target_w) / 2.0
        target_y = page_rect.top() + (page_rect.height() - target_h) / 2.0
        
        target_rect = QRectF(target_x, target_y, target_w, target_h)
        ws.scene.render(painter, target=target_rect, source=rect)
        painter.end()

    def export_md(self):
        """Génère un fichier Markdown structurant de manière textuelle la hiérarchie de la mindmap."""
        ws = self.app.current_workspace()
        if not ws: return
        
        nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
        if not nodes:
            QMessageBox.warning(self.app, "Export impossible", "La carte mentale ne contient aucun nœud.")
            return
            
        default_name = self._get_default_filename(ws, "md")
        path, _ = QFileDialog.getSaveFileName(self.app, "Exporter Markdown", default_name, "Markdown (*.md)")
        if not path: return
        
        # Identification du nœud racine
        root = next((n for n in nodes if n.node_id == 'root'), nodes[0])
        
        output = []
        visited = set()  # Protection anti-cycles infinis

        def build_tree(node, depth):
            if not node or node.node_id in visited: 
                return
            visited.add(node.node_id)
            
            clean_label = getattr(node, 'label', '').replace('\n', ' ')
            additions = []
            if getattr(node, 'file_path', None): additions.append(f"Fichier: {node.file_path}")
            if getattr(node, 'url_link', None): additions.append(f"URL: {node.url_link}")
            link_str = f" ({', '.join(additions)})" if additions else ""
            
            output.append(f"{'  ' * depth}- {clean_label}{link_str}")
            
            # Récupération sécurisée des nœuds enfants reliés
            if hasattr(node, 'edges'):
                children = [e.dest_node for e in node.edges if e.source_node == node and hasattr(e, 'dest_node')]
                for child in children: 
                    build_tree(child, depth + 1)
                
        build_tree(root, 0)
        
        # Écriture sécurisée avec capture d'erreurs I/O
        try:
            with open(path, 'w', encoding='utf-8') as f: 
                f.write("\n".join(output))
        except Exception as e:
            QMessageBox.critical(self.app, "Erreur d'écriture", f"Impossible d'enregistrer le fichier Markdown :\n{e}")