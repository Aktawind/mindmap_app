import webview
import os

def main():
    # Récupérer le chemin absolu du fichier index.html
    html_path = os.path.abspath("index.html")
    
    # Créer la fenêtre de l'application
    window = webview.create_window(
        title="Ma MindMap App - Concept V1",
        url=html_path,
        width=1024,
        height=768,
        resizable=True,
        min_size=(800, 600)
    )
    
    webview.start(debug=False)

if __name__ == "__main__":
    main()