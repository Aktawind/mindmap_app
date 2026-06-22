🧪 Test 1 : L'état initial "invisible" de la Barre de Style
Actions :

Lance l'application.

Regarde l'écran principal sans sélectionner aucun nœud ni aucune branche.

Résultat attendu :

La barre d'outils (StyleBar) doit être complètement invisible au démarrage.

L'overlay d'aide (les commandes de raccourcis) doit, lui, être visible en haut à gauche (à la position 20, 100) et afficher le texte d'aide de manière parfaitement lisible sans texte tronqué.

🧪 Test 2 : Le piège de l'argument du signal sur les boutons de couleur
Actions :

Crée ou sélectionne un nœud pour faire apparaître la StyleBar.

Clique sur le tout premier bouton de couleur (le bleu ciel).

Résultat attendu :

Le nœud sélectionné doit changer de couleur (fond bleu, bordure bleue plus foncée).

Important : L'application ne doit pas crasher. Si la correction du lambda n'est pas appliquée, PyQt envoie un booléen caché (checked) qui décale les arguments et fait planter la fonction avec une erreur du type TypeError: change_color() takes 2 positional arguments but 3 were given.

🧪 Test 3 : L'isolation des sections (Nœuds vs Branches)
Actions :

Sélectionne un nœud sur ton graphique.

Observe les boutons disponibles, puis désélectionne le nœud et sélectionne une branche (un lien/edge).

Résultat attendu :

Quand un nœud est sélectionné, la section des lignes (edge_controls, comme "Texte de branche" et les flèches) ne devrait pas influencer le nœud de façon incohérente.

Quand une branche est sélectionnée, le bouton "Bold", le menu de formes (Rectangle, Losange...) et les boutons de fichiers joints doivent idéalement être grisés ou masqués, et le menu des flèches doit être pleinement fonctionnel.

🧪 Test 4 : Persistance du choix des ComboBox (Formes & Statuts)
Actions :

Sélectionne un nœud.

Change la forme en "Losange" via la liste déroulante.

Change le statut en "🚨 Urgent".

Clique dans le vide pour désélectionner le nœud, puis clique à nouveau sur ce même nœud.

Résultat attendu :

Lors de la re-sélection, les listes déroulantes de la barre de style doivent se mettre à jour pour ré-afficher "Losange" et "🚨 Urgent" (et non pas revenir à "Rectangle" et "Aucun statut" par défaut).