## Cas de Test 1 : Création de nœud et héritage de couleur (Root vs Branche)
Action 1.1 : Sélectionnez le nœud central Root et appuyez sur Tab. Répétez l'opération 3 fois de suite pour créer 3 nœuds enfants.
Résultat attendu : Les 3 nœuds se placent automatiquement en cascade à droite de la racine. Ils possèdent chacun une couleur de contour/fond différente

Action 1.2 : Sélectionnez un des sous-nœuds fraîchement créés, puis créez-lui un enfant.
Résultat attendu : Ce nouveau sous-enfant adopte exactement la même couleur que son nœud parent, conservant ainsi la cohérence visuelle de la branche.

## Cas de Test 2 : Algorithme anti-chevauchement (Smart Position)
Action : Sélectionnez le nœud central Root. Créez un enfant, laissez le texte par défaut et validez. Sélectionnez à nouveau la racine Root et créez un second enfant.

Résultat attendu : Le deuxième nœud détecte la présence du premier. Il doit automatiquement se décaler vers le bas (de 85 pixels) pour s'afficher proprement sans recouvrir le premier nœud.

## Cas de Test 3 : Sécurité d'exclusion de la Racine et nettoyage (delete_selected)
Action 3.1 : Sélectionnez le nœud central Root uniquement et appuyez sur la touche Suppr (ou déclenchez delete_selected).
Résultat attendu : Le nœud central ne bouge pas et reste sur la scène. L'opération est ignorée (protection active).

Action 3.2 : Sélectionnez un nœud enfant possédant un sous-enfant et une pièce jointe, puis supprimez-le.
Résultat attendu : Le nœud et ses lignes de liaisons associées disparaissent de la scène. Le sous-enfant, s'il n'était relié qu'à lui, est détaché graphiquement de manière propre.

## Cas de Test 4 : Liaison libre entre deux nœuds (connect_selected_nodes)
Action : À l'aide de la touche Ctrl maintenue, sélectionnez deux nœuds distincts de votre carte mentale (qui n'ont aucun lien direct entre eux), puis lancez l'action de connexion (connect_selected_nodes).

Résultat attendu : Une nouvelle ligne de relation se dessine instantanément entre les deux éléments. La ligne prend automatiquement la couleur de bordure du premier nœud sélectionné.