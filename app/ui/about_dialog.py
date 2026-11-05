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

    <p><b>Nouveautés de la version 1.10.0 :</b></p>
    <ul>
        <li>Fichier .mindy autonome : il contient la carte, les images et les pièces jointes copiées, il suffit de le donner</li>
        <li>Liens entre fiches : bouton 🔗 ou [[ pour lier un autre nœud, un clic ouvre sa fiche ; chaque fiche indique où elle est « Citée dans »</li>
        <li>Liens web dans les notes : reconnus automatiquement et ouverts d'un clic</li>
        <li>Notes enrichies : titres, surligneur, cases à cocher, tableaux et emojis (avec les récents)</li>
        <li>Menu Exporter : export des notes en PDF ou en Word, dans l'ordre de la carte</li>
        <li>Menu Fichier &gt; Options : police et taille par défaut des notes</li>
    </ul>

    <p><b>Nouveautés de la version 1.9.2 :</b></p>
    <ul>
        <li>Mise à jour automatique fiabilisée : la nouvelle version est installée avant la fermeture de Mindy</li>
    </ul>

    <p><b>Nouveautés de la version 1.9.1 :</b></p>
    <ul>
        <li>Coller une image dans les notes (Ctrl+V) ou y glisser un fichier image</li>
        <li>Images des notes nettes, ajustées à la largeur de la fenêtre et redimensionnables à la souris</li>
        <li>Images rangées à côté de la carte : la carte et son dossier se déplacent ensemble</li>
        <li>Le nettoyage automatique ne supprime plus les images des notes ni celles des autres cartes du dossier</li>
    </ul>

    <p><b>Nouveautés de la version 1.9.0 :</b></p>
    <ul>
        <li>Menu Fichier &gt; Options : nombre de caractères avant retour à la ligne automatique</li>
        <li>Justification du texte des nœuds (gauche, centre, droite)</li>
        <li>Sélecteur d'emojis intégré (bouton 😀 ou Ctrl+E pendant la saisie)</li>
        <li>Zone de saisie qui s'agrandit avec le texte, sans barre de défilement</li>
        <li>Liens parfaitement droits entre deux nœuds face à face</li>
        <li>« Relier les nœuds » rattache un nœud isolé comme enfant, pris en compte par le pliage</li>
        <li>Pliage/dépliage des branches fiabilisé</li>
        <li>Taille et position des fenêtres (principale et notes) mémorisées</li>
        <li>Calendrier des échéances adapté au thème sombre</li>
    </ul>

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