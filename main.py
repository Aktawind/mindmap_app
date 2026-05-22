import webview
import os
import json
import base64
import logging
import sys

# Désactive la résolution DNS (getfqdn) très lente du serveur HTTP local de Python
from http.server import BaseHTTPRequestHandler
BaseHTTPRequestHandler.address_string = lambda self: self.client_address[0]

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
                return str(e)
        return "Fichier introuvable"

    def save_project(self, data_base64, force_save_as=False):
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
            data_json = base64.b64decode(data_base64).decode('utf-8')
            with open(self.current_file_path, 'w', encoding='utf-8') as f: 
                f.write(data_json)
            filename = os.path.basename(self.current_file_path)
            self.update_window_title(filename)
            return True 
        except Exception as e: 
            return f"Erreur d'écriture : {str(e)}"

    def load_project(self):
        if not self.window: return None
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            file_types=('JSON Files (*.json)', 'All files (*.*)')
        )
        if not result: return "Annulé"
        self.current_file_path = result[0] if isinstance(result, tuple) else result
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f: 
                data_json = f.read()
            encoded_bytes = base64.b64encode(data_json.encode('utf-8'))
            filename = os.path.basename(self.current_file_path)
            self.update_window_title(filename)
            return encoded_bytes.decode('utf-8')
        except Exception as e: 
            return None

    def export_markdown(self, markdown_base64):
        if not self.window: return False
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG, 
            file_types=('Markdown Files (*.md)', 'All files (*.*)'), 
            save_filename='ma_mindmap.md'
        )
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                markdown_text = base64.b64decode(markdown_base64).decode('utf-8')
                with open(file_path, 'w', encoding='utf-8') as f: 
                    f.write(markdown_text)
                return True
            except Exception as e: 
                return f"Erreur : {str(e)}"
        return "Annulé"

    def update_window_title(self, filename):
        if self.window:
            self.window.set_title(f"Mindy - {filename}")

def main():
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (
        '--disable-renderer-accessibility '
        '--disable-features=LayoutNG,AccessibilityObjectModel,LiveCaption '
        '--allow-file-access-from-files '
        '--disable-web-security '
        '--disable-gpu '
        '--disable-gpu-compositing '
        '--disable-accelerated-2d-canvas '
        '--disable-gpu-sandbox'
        '--proxy-server="direct://"'
    )
    
    if getattr(sys, 'frozen', False):
        project_dir = sys._MEIPASS
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
    icon_path = os.path.join(project_dir, "icon.ico")
    api = MindMapAPI()
    
    window = webview.create_window(
        title="Mindy - MindMap App",
        url=os.path.join(project_dir, "index.html"),
        width=1500,
        height=850,
        min_size=(900, 600),
        js_api=api,
        background_color='#f8f9fa'
    )
    
    api.set_window(window)
    # AJOUT DE DEBUG=TRUE POUR ACTIVER LE CLIC DROIT / INSPECTEUR
    webview.start(main, window, debug=True, icon=icon_path if os.path.exists(icon_path) else None)

if __name__ == '__main__':
    main()