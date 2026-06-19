## AttachmentController
__init__(self, app) : Initialise le contrôleur en conservant une référence vers l'application principale (app).

get_attachments_dir(self) : Résout et crée de manière sécurisée le dossier caché .mindmap_attachments au même emplacement que le fichier de sauvegarde actuel de la carte.

remove_file_from_attachments(self, relative_path) : Supprime proprement un fichier local. Sécurisé contre les failles de traversée de répertoire (Path Traversal) en vérifiant strictement que le chemin résolu se trouve bien à l'intérieur du dossier d'onglets.

copy_file_to_attachments(self, node_id, source_path) : Copie un fichier externe dans le répertoire de l'application en le renommant de manière unique (file_{node_id}.ext) afin d'éviter les collisions de noms.

attach_file(self) : Logique UI pour ouvrir un explorateur de fichiers, copier la pièce jointe ciblée et rafraîchir l'affichage du nœud sélectionné. Simplification : centralisation de la mise à jour visuelle du nœud pour éviter les répétitions.

attach_url(self) : Ouvre une boîte de dialogue pour associer ou modifier un lien hypertexte sur un nœud.

detach_links(self) : Supprime à la fois les fichiers locaux et l'URL associés au nœud sélectionné en nettoyant le disque si nécessaire.

open_file(self) : Résout le chemin d'accès absolu d'un fichier joint et demande au système d'exploitation de l'ouvrir avec l'application par défaut. Bascule automatiquement sur l'URL si aucun fichier n'est présent.

open_url(self) : Valide le format de la chaîne de caractères et lance le navigateur web par défaut du système.

## EditingController

__init__(self, app) : Initialise le contrôleur d'édition et hérite de QObject pour pouvoir utiliser les filtres d'événements Qt.

start_inline_editing(self, item) : Génère dynamiquement un composant QTextEdit au-dessus du nœud ou du lien sélectionné, nettoie les émojis de statut pour l'édition, et lui donne le focus graphique.

eventFilter(self, obj, event) : Intercepte les entrées clavier de l'éditeur. Valide avec Entrée (sauf si Maj est enfoncé pour faire un retour à la ligne) et annule avec Échap.

commit_edit(self) : Récupère le texte saisi, réinjecte les émojis de statut initiaux, met à jour l'élément graphique, redimensionne le nœud et enregistre l'état du projet.

cancel_edit(self) : Ferme l'éditeur instantanément sans modifier le texte d'origine.

on_tab_pressed(self) : Permet de créer un sous-nœud enfant si la touche Tab est pressée alors qu'aucun éditeur n'est actif.

edit_selected_edge(self) : Déclenche manuellement l'édition textuelle sur une ligne de liaison (EdgeItem) sélectionnée.