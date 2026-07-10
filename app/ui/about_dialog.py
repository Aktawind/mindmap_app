from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt

def show_app_about_dialog(app_window, version_str):
    """Affiche la boîte de dialogue 'À propos' de l'application avec un rendu HTML garanti."""
    about_text = f"""
    <h3>Mindy — Éditeur de Mind Mapping</h3>
    <p><b>Version :</b> v{version_str}</p>
    <p><b>Développeur :</b> Audrey DEAL</p>
    <hr>
    <p>Mindy est une application intuitive conçue pour structurer vos idées, 
    créer des cartes mentales fluides et exporter vos projets dans des formats variés.</p>
    
    <p><b>Fonctionnalités clés :</b></p>
    <ul>
        <li>Routage de lignes dynamique</li>
        <li>Gestion multi-onglets et espace de travail</li>
        <li>Système de Snap to Grid (Grille magnétique)</li>
        <li>Intégration d'images haute qualité avec redimensionnement automatique des nœuds</li>
        <li>Ajout de pièces jointes locales et de liens URL sur les nœuds</li>
    </ul>
    <br>
    <p><small>© 2026 Mindy App. Tous droits réservés.</small></p>
    """
    
    # Sécurité si app_window est None
    msg = QMessageBox(app_window) if app_window else QMessageBox()
    msg.setWindowTitle("À propos de Mindy")
    
    # 🚨 FIX CRITIQUE : On force Qt à interpréter la chaîne comme du HTML/RichText
    msg.setTextFormat(Qt.TextFormat.RichText)
    msg.setText(about_text)
    
    msg.setIcon(QMessageBox.Icon.Information)
    
    # Sécurité sur l'extraction de l'icône de la fenêtre principale
    if app_window and hasattr(app_window, 'windowIcon') and not app_window.windowIcon().isNull():
        msg.setWindowIcon(app_window.windowIcon())
        
    msg.exec()