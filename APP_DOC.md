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

