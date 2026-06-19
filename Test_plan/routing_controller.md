Cas de Test 1 : Alternance du style des liens
Action : Créez une Mind Map avec au moins 3 niveaux de nœuds (Racine -> Enfant -> Sous-enfant) pour avoir plusieurs lignes bien visibles. Cliquez sur le bouton de liens courbes/droits
Résultat attendu :
Le texte du bouton bascule instantanément entre "Liens droits" et "Liens courbes".
Toutes les lignes reliant vos nœuds changent de forme en temps réel sur l'écran : elles passent de lignes brisées orthogonales/droites à de belles courbes lissées, sans déconnexion des nœuds.

Cas de Test 2 : Modification du sens des flèches
Action : Cliquez sur une arête (une ligne de liaison) pour la sélectionner. Votre barre de style s'affiche (grâce au gestionnaire de sélection validé précédemment). Modifiez la valeur de la liste déroulante des flèches (arrow_combo) en choisissant une direction (ex: "Bidirectionnelle" ou "Inverse").

Résultat attendu :
Le dessin de la flèche sur la ligne se met immédiatement à jour pour pointer dans la direction choisie.

Cas de Test 3 : Persistance du style de routage
Action : Changez le mode de routage (ex: activez "Liens courbes"). Modifiez le texte d'un nœud pour forcer l'application à faire un save_state. Fermez l'application et relancez-la (ou faites un Ctrl+Z / Ctrl+Y si implémenté).

Résultat attendu : Le mode choisi ("Liens courbes") doit être conservé et le rendu visuel doit être identique à l'état avant fermeture.

Cas de Test 5 (Nouveau) : Robustesse géométrique après chargement
Action : Chargez une Mind Map enregistrée. Prenez n'importe quel nœud enfant à la souris et déplacez-le sur la scène.

Résultat attendu : Les lignes de liaisons reliées à ce nœud doivent suivre le mouvement de façon parfaitement fluide et synchrone (preuve que la reconstruction des listes node.edges en mémoire fonctionne à 100%).