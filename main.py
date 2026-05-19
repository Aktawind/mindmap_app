import webview
import os
import json
import base64

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
        
        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})
        return None

    def load_template(self, template_name):
        """Lit un fichier template JSON local et renvoie son contenu"""
        safe_name = os.path.basename(template_name)
        template_path = os.path.join("templates", safe_name)
        
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": "Template introuvable"})

    def export_png(self, base64_data):
        """Prend la chaîne base64 du canvas, la décode et l'enregistre en PNG"""
        if not self.window:
            return "Erreur d'initialisation de la fenêtre"

        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            file_types=('PNG Image (*.png)', 'All files (*.*)'),
            save_filename='ma_mindmap.png'
        )

        if result:
            file_path = result[0] if isinstance(result, tuple) else result
            try:
                # Nettoyage de l'entête de la chaîne Data URL si présente
                if "," in base64_data:
                    base64_data = base64_data.split(",")[1]

                # Décodage des données de l'image
                image_bytes = base64.b64decode(base64_data)

                # Écriture du fichier binaire
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                return f"🖼️ Image exportée avec succès : {os.path.basename(file_path)}"
            except Exception as e:
                return f"Erreur lors de l'export de l'image : {str(e)}"
        return "Export annulé"

def main():
    html_path = os.path.abspath("index.html")
    api = MindMapAPI()
    
    window = webview.create_window(
        title="Ma MindMap App - Workspace Pro",
        url=html_path,
        width=1200,
        height=850,
        resizable=True,
        js_api=api
    )
    
    api.set_window(window)
    webview.start(debug=False)

if __name__ == "__main__":
    main()