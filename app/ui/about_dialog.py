# ui/about_dialog.py
from PyQt6.QtWidgets import QMessageBox

def show_app_about_dialog(app_window, version_str):
    """Affiche la boîte de dialogue 'À propos' de l'application."""
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
        <li>Système de Snap to Grid</li>
        <li>Ajout de pièces jointes et de liens URL sur les nœuds</li>
    </ul>
    <br>
    <p><small>© 2026 Mindy App. Tous droits réservés.</small></p>
    """
    
    msg = QMessageBox(app_window)
    msg.setWindowTitle("À propos de Mindy")
    msg.setText(about_text)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowIcon(app_window.windowIcon())
    msg.exec()