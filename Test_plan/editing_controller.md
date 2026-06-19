## Cas de Test 1 : Lancement et validation par touche Entrée
Action : Double-cliquez sur un nœud existant. Saisissez un nouveau texte (ex: "Nouveau Nœud") et appuyez sur la touche Entrée.
Résultat attendu : * L'encadré d'édition bleu apparaît pile au-dessus du nœud.
À l'appui sur Entrée, l'éditeur disparaît, le nœud se redimensionne correctement par rapport à la taille du texte et la modification reste visible.

## Cas de Test 2 : Retour à la ligne (Shift + Entrée)
Action : Ouvrez à nouveau l'éditeur sur un nœud. Écrivez une première ligne, puis faites la combinaison Maj + Entrée (Shift + Enter). Écrivez une deuxième ligne, puis validez avec Entrée seule.
Résultat attendu :
L'appui sur Shift + Entrée doit créer un saut de ligne dans l'éditeur sans valider ni fermer la boîte.
Après validation finale, le nœud affiche le texte sur deux lignes distinctes.

## Cas de Test 3 : Annulation via la touche Échap
Action : Ouvrez l'éditeur sur un nœud. Modifiez le texte en tapant n'importe quoi, puis appuyez sur la touche Échap.
Résultat attendu :
L'éditeur se ferme immédiatement.
Le nœud conserve son texte d'origine, aucune modification n'est appliquée.

## Cas de Test 4 : Sauvegarde automatique par perte de focus (FocusOut)
Action : Ouvrez l'éditeur sur un nœud. Modifiez son texte, puis cliquez n'importe où ailleurs sur le canevas de la Mind Map (dans le vide) avec votre souris sans appuyer sur aucune touche.
Résultat attendu :
Dès que le clic se produit à l'extérieur, l'éditeur détecte la perte de focus, se ferme et applique automatiquement vos modifications de texte.

## Cas de Test 5 : Préservation des Badges de Statut (Émojis)
Action : Mettez un statut sur un nœud (par exemple en "Urgent" pour faire apparaître l'émoji 🚨). Ouvrez l'éditeur sur ce nœud.
Résultat attendu :
La zone de texte d'édition s'ouvre mais l'émoji 🚨 ne doit pas être présent dans la zone éditable (le texte doit être épuré).
Modifiez le texte et validez. Le nœud doit réapparaître modifié tout en ayant conservé son émoji 🚨 au début.

## Cas de Test 6 : Édition d'une liaison (EdgeItem)
Action : Sélectionnez une ligne de liaison (un trait reliant deux nœuds) et déclenchez l'action associée à edit_selected_edge.
Résultat attendu :
Une zone de saisie textuelle apparaît précisément au milieu de la ligne pour vous permettre de nommer ou qualifier la relation.