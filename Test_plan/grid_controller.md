## Cas de Test 1 : Sécurité hors-contexte
Action : Fermez tous vos onglets ou mindmaps ouverts pour vous retrouver sur l'écran d'accueil vide de l'application. Activez/désactivez l'option de grille (via votre raccourci, menu ou bouton).

Résultat attendu : L'application ne plante pas. L'action est ignorée de manière transparente et sécurisée.

## Cas de Test 2 : Alignement de masse instantané
Action : Ouvrez une Mind Map. Désactivez temporairement l'aimantation. Bougez plusieurs nœuds à la souris de manière désordonnée pour qu'ils soient complètement désalignés (ex: un pixel par-ci, un pixel par-là). Activez ensuite le bouton de la grille.

Résultat attendu : Tous les nœuds de la scène font un léger "saut" visuel pour venir se verrouiller parfaitement sur les lignes imaginaires de la grille de 20px.

## Cas de Test 3 : Alignement des lignes (Correctif)
Action : Regardez attentivement les traits (les arêtes) qui relient vos nœuds juste après avoir activé la grille à l'étape précédente.

Résultat attendu : Grâce à l'appel de mise à jour des arêtes, les lignes doivent rester parfaitement connectées aux centres ou aux bordures des nœuds. Aucun trait ne doit flotter anormalement dans le vide ou pointer vers l'ancienne position d'un nœud.