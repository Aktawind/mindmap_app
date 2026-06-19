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

## ExportController
__init__(self, app) : Constructeur standard. Stocke la référence de l'application.

export_png(self) : Exporte la zone active de la scène au format raster PNG. Le code prend déjà bien en compte le facteur d'échelle des écrans haute densité (Retina/4K) grâce au ratio, ce qui évite d'avoir des images floues. Ajout d'une sécurité sur rectangle vide.

export_pdf(self) : Effectue un rendu vectoriel haute définition à l'échelle sur une page A4. Ajuste automatiquement l'orientation (Paysage ou Portrait) selon la forme globale de la mindmap.

export_md(self) : Extrait la structure sémantique de la mindmap pour générer une liste à puces hiérarchique au format Markdown (.md), incluant les fichiers joints et les liens URL trouvés.

## GraphController
__init__(self, app) : Initialise le contrôleur de graphe.

add_child_node(self, parent_node) : Crée un sous-nœud rattaché, hérite dynamiquement des couleurs de sa branche mère (ou sélectionne une nouvelle palette du fichier graphics.items s'il part de la racine), génère son arête de liaison, l'ajoute à la scène Qt et bascule automatiquement l'interface utilisateur en mode édition.

calculate_smart_position(self, parent_node) : Algorithme prédictif de positionnement. Il projette le nouveau nœud à droite de son parent et applique une boucle de détection de collisions pour décaler verticalement la boîte si l'espace est déjà occupé.

delete_selected(self) : Supprime proprement tous les éléments sélectionnés (nœuds et arêtes), détache les liaisons en cascade des nœuds adjacents pour éviter les pointeurs corrompus, et délègue la suppression physique des pièces jointes associées.

connect_selected_nodes(self) : Permet de créer un lien personnalisé de cause à effet entre deux nœuds distincts sélectionnés simultanément, après avoir validé qu'ils ne sont pas déjà connectés.

## GridController
toggle_snap_to_grid(self, checked) : Active ou désactive l'état d'aimantation globale de la scène. Si l'option est activée (checked=True), elle applique immédiatement un traitement de rafraîchissement géométrique sur chaque nœud pour le caler sur le multiple de 20 pixels le plus proche (grille virtuelle de 20x20) et recalcule l'affichage des lignes.

## RoutingController
update_routing_button_ui(self) : Aligne dynamiquement le libellé textuel du bouton de l'interface en fonction de son état enfoncé ou relâché ("Liens courbes" vs "Liens droits").

toggle_line_routing(self, checked) : Modifie le mode de rendu global des connexions de la scène ('curved' ou 'orthogonal'), puis passe en revue toutes les arêtes de la carte pour recalculer instantanément leurs courbes ou angles.

on_arrow_combo_changed(self, index) : Intercepte le changement de sélection dans la liste déroulante des flèches pour modifier la direction de la flèche du lien sélectionné (ex: Source vers Destination, Destination vers Source, ou Bidirectionnel).

## StyleController