import webview
import os
import json
import base64
import logging
import sys

# --- PATCH ANTI-FREEZE 10 SECONDES ---
# Désactive la résolution DNS (getfqdn) très lente du serveur HTTP local de Python
from http.server import BaseHTTPRequestHandler
BaseHTTPRequestHandler.address_string = lambda self: self.client_address[0]
# -------------------------------------

# Silence complet sur les avertissements pour maximiser les performances de communication
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger('pywebview')
logger.setLevel(logging.CRITICAL)

class MindMapAPI:
    def __init__(self):
        self.window = None
        self.current_file_path = None

    def set_window(self, window):
        self.window = window

    def select_local_file(self):
        if not self.window: return None
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            file_types=('Tous les fichiers (*.*)', 'Images (*.png;*.jpg;*.jpeg;*.gif)', 'Documents (*.pdf;*.docx;*.xlsx;*.txt)')
        )
        if result:
            return result[0] if isinstance(result, tuple) else result
        return None

    def open_local_file(self, file_path):
        if os.path.exists(file_path):
            try:
                os.startfile(file_path)
                return True
            except Exception as e:
                return f"Erreur d'ouverture : {str(e)}"
        return "Fichier introuvable"

    def update_window_title(self, suffix=None):
        if not self.window: return
        base_title = "MindMap App"
        if suffix:
            self.window.set_title(f"{base_title} - {suffix}")
        else:
            self.window.set_title(base_title)

    def save_project(self, data_json, force_save_as=False):
        if not self.window: return False
        if not self.current_file_path or force_save_as:
            result = self.window.create_file_dialog(
                webview.SAVE_DIALOG, 
                file_types=('JSON Files (*.json)', 'All files (*.*)'), 
                save_filename='ma_mindmap.json'
            )
            if not result: return "Annulé"
            self.current_file_path = result[0] if isinstance(result, tuple) else result
        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f: 
                f.write(data_json)
            filename = os.path.basename(self.current_file_path)
            self.update_window_title(filename)
            return True 
        except Exception as e: 
            return f"Erreur d'écriture : {str(e)}"

    def load_project(self):
        if not self.window: return None
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=('JSON Files (*.json)', 'All files (*.*)'))
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                self.current_file_path = file_path
                filename = os.path.basename(file_path)
                self.update_window_title(filename)
                return json.dumps({"content": content, "filename": filename})
            except Exception as e: 
                return json.dumps({"error": str(e)})
        return None

    def reset_current_path(self):
        self.current_file_path = None
        self.update_window_title("[Nouveau Projet]")

    def load_template(self, template_name):
        safe_name = os.path.basename(template_name)
        if getattr(sys, 'frozen', False):
            template_path = os.path.join(sys._MEIPASS, "templates", safe_name)
        else:
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", safe_name)
            
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f: return f.read()
            except Exception as e: return json.dumps({"error": str(e)})
        return json.dumps({"error": "Template introuvable"})

    def export_png(self, base64_data):
        if not self.window: return "Erreur"
        result = self.window.create_file_dialog(webview.SAVE_DIALOG, file_types=('PNG Image (*.png)', 'All files (*.*)'), save_filename='ma_mindmap.png')
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                if "," in base64_data: base64_data = base64_data.split(",")[1]
                with open(file_path, 'wb') as f: f.write(base64.b64decode(base64_data))
                return True
            except Exception as e: return f"Erreur : {str(e)}"
        return "Annulé"

    def export_markdown(self, markdown_text):
        if not self.window: return False
        result = self.window.create_file_dialog(webview.SAVE_DIALOG, file_types=('Markdown Files (*.md)', 'All files (*.*)'), save_filename='ma_mindmap.md')
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(markdown_text)
                return True
            except Exception as e: return f"Erreur : {str(e)}"
        return "Annulé"


def main():
    # Options Windows WebView2 de bas niveau obligatoires pour stabiliser les threads
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (
        '--disable-renderer-accessibility '
        '--disable-features=LayoutNG,AccessibilityObjectModel,LiveCaption '
        '--allow-file-access-from-files '
        '--disable-web-security '
        '--disable-gpu '
        '--disable-gpu-compositing '
        '--disable-accelerated-2d-canvas '
        '--disable-gpu-sandbox'

        '--proxy-server="direct://"' # <--- AJOUT IMPORTANT ICI
    )
    
    if getattr(sys, 'frozen', False):
        project_dir = sys._MEIPASS
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
    icon_path = os.path.join(project_dir, "icon.ico")
    api = MindMapAPI()
    
    # SOLUTION RADICALE : On pointe vers le fichier index.html local, mais...
    window = webview.create_window(
        title="MindMap App",
        url=os.path.join(project_dir, "index.html"),
        width=1500, height=850, resizable=True, js_api=api
    )
    api.set_window(window)
    
    # ... ON FORCE LE MODE SERVEUR HTTP EMBARQUÉ INTÉGRÉ (http_server=True)
    # Pywebview va automatiquement créer un serveur local sur un port aléatoire libre.
    # Les requêtes JS <=> Python passent par un tunnel réseau local asynchrone, ce qui supprime le freeze.
    webview.start(
        debug=False, 
        http_server=True,
        icon=icon_path if os.path.exists(icon_path) else None
    )

if __name__ == "__main__":
    main()