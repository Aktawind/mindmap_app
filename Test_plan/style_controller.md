Cas de Test 1 : Cascade de couleurs et protection cyclique
Action : Créez un nœud Parent, un Enfant, et un Sous-Enfant. Reliez via un lien transversal (bouton Relier) le Sous-Enfant directement au Parent (création d'un cycle). Sélectionnez le nœud Parent et appliquez une nouvelle couleur.

Résultat attendu : L'application applique la couleur sur toute la descendance en cascade de façon instantanée, et ne plante pas malgré la présence de la boucle fermée.

Cas de Test 2 : Commutation des formes et alignement des traits
Action : Sélectionnez un nœud rectangulaire relié à plusieurs enfants. Changez sa forme en cercle via la combobox shape_combo.

Résultat attendu : Le nœud se transforme en cercle. Grâce aux correctifs, les lignes s'ajustent parfaitement et viennent mourir sur le nouveau contour circulaire sans flotter à l'extérieur.

Cas de Test 3 : Changement de statut (Sans perte du texte)
Action : Prenez un nœud nommé "Faire les tests". Changez son statut en "Urgent". Remplacez-le ensuite par "Terminé".

Résultat attendu : Le texte devient "🚨 Faire les tests" puis se transforme proprement en "✅ Faire les tests" sans accumuler ou dupliquer les emojis de façon anarchique.  