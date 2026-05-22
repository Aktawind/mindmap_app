import os
import sys
import json
import base64
from PyQt6.QtCore import QUrl, QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

class MindMapBridge(QObject):
    """Pont de communication asynchrone entre l'interface JS et l'OS via PyQt6"""
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_file_path = None

    @pyqtSlot()
    def reset_current_path(self):
        """Réinitialise le chemin du fichier courant (Nouveau projet)"""
        self.current_file_path = None

    @pyqtSlot(result=str)
    def load_project_dialog(self):
        """Ouvre un projet avec une boîte de dialogue native Windows"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "Ouvrir un projet", "", "MindMap Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.current_file_path = file_path
                self.window.setWindowTitle(f"MindMap App - [{os.path.basename(file_path)}]")
                # On retourne un objet JSON valide contenant le contenu
                return json.dumps({"status": "success", "content": content})
            except Exception as e:
                return json.dumps({"status": "error", "message": str(e)})
        return ""

    @pyqtSlot(str, bool, result=str)
    def save_project_dialog(self, json_data, force_save_as):
        """Sauvegarde ou Enregistre sous le projet courant"""
        file_path = self.current_file_path
        
        if force_save_as or not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self.window, "Enregistrer le projet", 
                file_path if file_path else "ma_mindmap.json", 
                "MindMap Files (*.json)"
            )
            
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                self.current_file_path = file_path
                self.window.setWindowTitle(f"MindMap App - [{os.path.basename(file_path)}]")
                return "true"
            except Exception as e:
                return f"Erreur : {str(e)}"
        return "Annulé"

    @pyqtSlot(str, result=str)
    def load_template(self, template_name):
        """Charge un fichier template local depuis le répertoire racine ou l'exécutable"""
        template_path = os.path.join(self.window.base_dir, template_name)
        if os.path.exists(template_path):
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": f"Template {template_name} introuvable."})

    @pyqtSlot(result=str)
    def select_local_file(self):
        """Sélectionne un fichier local à associer en pièce jointe"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "Associer un document", "", "Tous les fichiers (*.*)"
        )
        return file_path if file_path else ""

    @pyqtSlot(str, result=str)
    def open_local_file(self, file_path):
        """Ouvre une pièce jointe avec l'application système par défaut"""
        if os.path.exists(file_path):
            try:
                os.startfile(file_path)
                return "true"
            except Exception as e:
                return str(e)
        return "Le fichier spécifié est introuvable."

    @pyqtSlot(str, str)
    def export_file(self, content, file_type):
        """Exécute l'export de fichiers natifs (PNG / Markdown)"""
        if file_type == "png":
            file_path, _ = QFileDialog.getSaveFileName(self.window, "Exporter en Image", "mindmap.png", "Images (*.png)")
            if file_path:
                try:
                    header, encoded = content.split(",", 1)
                    data = base64.b64decode(encoded)
                    with open(file_path, "wb") as f:
                        f.write(data)
                except Exception as e:
                    QMessageBox.critical(self.window, "Erreur d'export", str(e))
        elif file_type == "md":
            file_path, _ = QFileDialog.getSaveFileName(self.window, "Exporter en Markdown", "mindmap.md", "Markdown (*.md)")
            if file_path:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception as e:
                    QMessageBox.critical(self.window, "Erreur d'export", str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MindMap App - [Nouveau Projet]")
        self.setGeometry(100, 100, 1500, 850)

        if getattr(sys, 'frozen', False):
            self.base_dir = sys._MEIPASS
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        icon_path = os.path.join(self.base_dir, "icon.ico")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))

        self.browser = QWebEngineView()
        
        # Configuration de la liaison QWebChannel
        self.channel = QWebChannel()
        self.bridge = MindMapBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        html_path = os.path.abspath(os.path.join(self.base_dir, "index.html"))
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        
        self.setCentralWidget(self.browser)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())