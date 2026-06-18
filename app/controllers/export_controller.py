# controllers/export_controller.py
import os

from PyQt6.QtCore import QMarginsF, QRectF
from PyQt6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QImage, QPixmap
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtPrintSupport import QPrinter

from graphics.items import NodeItem

class ExportController:
    @staticmethod
    def export_png(app):
        ws = app.current_workspace()
        if not ws: return
        default_name = "ma_mindmap.png"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.png"
        path, _ = QFileDialog.getSaveFileName(app, "Exporter PNG", default_name, "PNG (*.png)")
        if path:
            ws.scene.clearSelection()
            rect = ws.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            
            ratio = app.devicePixelRatioF() if hasattr(app, 'devicePixelRatioF') else app.devicePixelRatio()
            
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
            pixmap.save(path, "PNG", 100)

    @staticmethod
    def export_pdf(app):
        ws = app.current_workspace()
        if not ws: return
        
        default_name = "ma_mindmap.pdf"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.pdf"
            
        path, _ = QFileDialog.getSaveFileName(app, "Exporter PDF Vectoriel", default_name, "PDF (*.pdf)")
        if path:
            ws.scene.clearSelection()
            
            # 1. On récupère les dimensions réelles occupées par le graphe (avec marge)
            rect = ws.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
            if rect.isEmpty(): return
            
            # 2. Utiliser ScreenResolution au lieu de HighResolution pour garder le bon ratio polices/formes
            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            
            # 3. Choix de l'orientation de la page
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
            
            # 4. Obtenir la zone de la page disponible en pixels de résolution logique
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            
            # 5. Calculer le ratio global pour que tout rentre proportionnellement
            scale_x = page_rect.width() / rect.width()
            scale_y = page_rect.height() / rect.height()
            scale = min(scale_x, scale_y)
            
            # 6. Définir un rectangle cible centré sur la page A4 qui respecte EXACTEMENT les proportions du graphe
            target_w = rect.width() * scale
            target_h = rect.height() * scale
            target_x = page_rect.left() + (page_rect.width() - target_w) / 2.0
            target_y = page_rect.top() + (page_rect.height() - target_h) / 2.0
            
            target_rect = QRectF(target_x, target_y, target_w, target_h)
            
            # 7. C'est scene.render() qui va gérer la mise à l'échelle harmonieuse des polices et des formes
            ws.scene.render(painter, target=target_rect, source=rect)
            painter.end()

    def export_md(app):
        ws = app.current_workspace()
        if not ws: return
        default_name = "ma_mindmap.md"
        if ws.current_file_path:
            base = os.path.splitext(os.path.basename(ws.current_file_path))[0]
            default_name = f"{base}.md"
            
        path, _ = QFileDialog.getSaveFileName(app, "Exporter Markdown", default_name, "Markdown (*.md)")
        if path:
            nodes = [i for i in ws.scene.items() if isinstance(i, NodeItem)]
            root = next((n for n in nodes if n.node_id == 'root'), nodes[0] if nodes else None)
            if not root: return
            
            output = []
            def build_tree(node, depth):
                clean_label = node.label.replace('\n', ' ')
                additions = []
                if node.file_path: additions.append(f"Fichier: {node.file_path}")
                if node.url_link: additions.append(f"URL: {node.url_link}")
                link_str = f" ({', '.join(additions)})" if additions else ""
                
                output.append(f"{'  ' * depth}- {clean_label}{link_str}")
                children = [e.dest_node for e in node.edges if e.source_node == node]
                for child in children: build_tree(child, depth + 1)
                    
            build_tree(root, 0)
            with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(output))