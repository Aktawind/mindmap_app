import webview
import os
import json
import base64
import logging

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger('pywebview')
logger.setLevel(logging.CRITICAL)

class MindMapAPI:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    # --- NOUVEAU : SÉLECTIONNER UN DOCUMENT OU IMAGE ---
    def select_local_file(self):
        if not self.window: return None
        # Ouvre un explorateur de fichiers générique
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            file_types=('Tous les fichiers (*.*)', 'Images (*.png;*.jpg;*.jpeg;*.gif)', 'Documents (*.pdf;*.docx;*.xlsx;*.txt)')
        )
        if result:
            return result[0] if isinstance(result, tuple) else result
        return None

    # --- NOUVEAU : OUVRIR LE DOCUMENT AVEC L'APPLICATION SYSTÈME PAR DÉFAUT ---
    def open_local_file(self, file_path):
        if os.path.exists(file_path):
            try:
                os.startfile(file_path) # Magie Windows : ouvre le PDF dans Acrobat, l'image dans Photos, etc.
                return True
            except Exception as e:
                return f"Erreur d'ouverture : {str(e)}"
        return "Fichier introuvable"

    # --- SECTION PERSISTANCE EXISTANTE ---
    def save_project(self, data_json):
        if not self.window: return False
        result = self.window.create_file_dialog(webview.SAVE_DIALOG, file_types=('JSON Files (*.json)', 'All files (*.*)'), save_filename='ma_mindmap.json')
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(data_json)
                return f"Sauvegardé avec succès"
            except Exception as e: return f"Erreur : {str(e)}"
        return "Annulé"

    def load_project(self):
        if not self.window: return None
        result = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=('JSON Files (*.json)', 'All files (*.*)'))
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'r', encoding='utf-8') as f: return f.read()
            except Exception as e: return json.dumps({"error": str(e)})
        return None

    def load_template(self, template_name):
        safe_name = os.path.basename(template_name)
        template_path = os.path.join("templates", safe_name)
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
                return "Image exportée"
            except Exception as e: return f"Erreur : {str(e)}"
        return "Annulé"

    def export_markdown(self, markdown_text):
        if not self.window: return False
        result = self.window.create_file_dialog(webview.SAVE_DIALOG, file_types=('Markdown Files (*.md)', 'All files (*.*)'), save_filename='ma_mindmap.md')
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(markdown_text)
                return "Structure exportée"
            except Exception as e: return f"Erreur : {str(e)}"
        return "Annulé"


def on_loaded(window):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    js_lib_path = os.path.join(project_dir, "vis-network.min.js")
    if os.path.exists(js_lib_path):
        with open(js_lib_path, 'r', encoding='utf-8') as f:
            window.evaluate_js(f.read())
            
    css_path = os.path.join(project_dir, "styles.css")
    if os.path.exists(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            window.load_css(f.read())
            
    window.evaluate_js("startMindMapEngine();")


def main():
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--disable-renderer-accessibility --disable-features=LayoutNG,AccessibilityObjectModel,LiveCaption'
    project_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(project_dir, "index.html")
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Erreur index.html : {e}")
        return

    api = MindMapAPI()
    window = webview.create_window(
        title="Ma MindMap App - Workspace Pro & Modulaire",
        html=html_content,
        width=1500, height=850, resizable=True, js_api=api
    )
    api.set_window(window)
    webview.start(on_loaded, window, debug=False)

if __name__ == "__main__":
    main()