🧪 Test 1 : L'activation des raccourcis "clavier uniquement"
Actions :

Lance l'application. Sans ouvrir le menu "Fichier" avec la souris, modifie la carte courante et tape directement Ctrl + S sur ton clavier.

Résultat attendu : La boîte de dialogue de sauvegarde (ou la confirmation) doit surgir immédiatement. Si le raccourci ne répond pas sans avoir cliqué sur le menu au moins une fois auparavant, c'était le bug de la destruction de la QAction évoqué plus haut.

🧪 Test 2 : La cascade du sous-menu "Espaces de travail"
Actions :

Clique sur "Fichier", puis passe ta souris sur "Espaces de travail".

Résultat attendu : Un sous-menu doit s'ouvrir latéralement de façon fluide et afficher les deux options "Nouvel espace de travail" et "Ouvrir un espace de travail". Aucun chevauchement graphique ne doit se produire.