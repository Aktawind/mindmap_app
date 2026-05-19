import webview
import os
import json

class MindMapAPI:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def save_project(self, data_json):
        """Ouvre une boîte de dialogue Windows pour sauvegarder le JSON"""
        if not self.window:
            return False
        
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG, 
            file_types=('JSON Files (*.json)', 'All files (*.*)'),
            save_filename='ma_mindmap.json'
        )
        
        if result:
            # FIX : Si pywebview renvoie un tuple (ex: ('chemin/fichier.json',)), on extrait le premier élément
            file_path = result[0] if isinstance(result, tuple) else result
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data_json)
                return f"Sauvegardé avec succès dans : {os.path.basename(file_path)}"
            except Exception as e:
                return f"Erreur lors de la sauvegarde : {str(e)}"
        return "Sauvegarde annulée"

    def load_project(self):
        """Ouvre une boîte de dialogue Windows pour charger un JSON"""
        if not self.window:
            return None
            
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            file_types=('JSON Files (*.json)', 'All files (*.*)')
        )
        
        if result and len(result) > 0:
            file_path = result[0]
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})
        return None
    
    def load_template(self, template_name):
        """Lit un fichier template JSON local et renvoie son contenu"""
        # Sécurisation du nom de fichier pour éviter les injections de chemin
        safe_name = os.path.basename(template_name)
        template_path = os.path.join("templates", safe_name)
        
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": "Template introuvable"})

def main():
    html_path = os.path.abspath("index.html")
    api = MindMapAPI()
    
    window = webview.create_window(
        title="Ma MindMap App - Persistance & Édition",
        url=html_path,
        width=1100,
        height=800,
        resizable=True,
        js_api=api
    )
    
    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()