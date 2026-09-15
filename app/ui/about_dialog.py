from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt

def show_app_about_dialog(app_window, version_str):
    """Affiche la boîte de dialogue 'À propos' de l'application avec un rendu HTML garanti."""
    about_text = f"""
    <h3>Mindy — Éditeur de Mind Mapping</h3>
    <p><b>Version :</b> {version_str}</p>
    <p><b>Développeur :</b> Audrey DEAL</p>
    <hr>
    <p>Mindy est une application intuitive conçue pour structurer vos idées,
    créer des cartes mentales fluides et les transformer en véritables tableaux
    de travail, grâce à ses canevas de fond, puis les exporter dans des formats variés.</p>

    <p><b>Cartes et organisation :</b></p>
    <ul>
        <li>Réorganisation automatique de l'arborescence</li>
        <li>Canevas de fond ancrés à la carte : Kanban, matrice d'Eisenhower, SWOT etc.</li>
        <li>Routage de lignes dynamique (courbes, orthogonal, diagonal, coudé)</li>
        <li>Gestion multi-onglets et espaces de travail</li>
        <li>Grille magnétique</li>
        <li>Modèles de cartes prêts à l'emploi, personnalisables et gérables dans l'application</li>
    </ul>

    <p><b>Nœuds et contenu :</b></p>
    <ul>
        <li>Statuts, priorités, échéances et formats de nœud personnalisables</li>
        <li>Palette de couleurs personnalisée, avec contraste de texte automatique</li>
        <li>Intégration d'images haute qualité avec redimensionnement automatique des nœuds</li>
        <li>Pièces jointes locales, liens URL et notes détaillées sur chaque nœud</li>
        <li>Copier/coller multi-nœuds, y compris d'un onglet à l'autre</li>
    </ul>

    <p><b>Fiabilité et export :</b></p>
    <ul>
        <li>Historique et sauvegarde automatique</li>
        <li>Export en image PNG haute résolution, PDF vectoriel et Markdown</li>
        <li>Vérification des mises à jour à la demande</li>
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
        
    msg.setStyleSheet("QLabel#qt_msgbox_label { min-width: 600px; }")
    msg.exec()