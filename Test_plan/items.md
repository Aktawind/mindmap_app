## 📋 Tests Manuels Avancés pour la Géométrie et le Rendu

### 🧪 Test 1 : Le crash des nœuds superposés (Division par Zéro / Convergence)

* **Objectif :** Tester la robustesse de votre fonction `get_exact_intersection` lorsque deux nœuds partagent exactement les mêmes coordonnées.
* **Actions :**
1. Activez le magnétisme de la grille (`snap_to_grid = True`).
2. Créez un Nœud A et un Nœud B.
3. Reliez-les par une branche (`EdgeItem`).
4. Prenez le Nœud B et déplacez-le de sorte qu'il soit **pile-poil superposé** sur le Nœud A (mêmes coordonnées X et Y).


* **Résultat attendu :** L'application ne doit pas planter (pas de `ZeroDivisionError` ni de boucle infinie). La ligne s'ajuste élégamment ou se réduit à un point invisible, mais l'interface reste réactive.

---

### 🧪 Test 2 : Le stress-test du Saut de Ligne (`\n`) et des Badges

* **Objectif :** Vérifier la précision de la méthode `recalculate_size` face au dimensionnement dynamique.
* **Actions :**
1. Modifiez le texte d'un nœud et insérez un titre très court sur la ligne 1, mais une phrase ultra longue sur la ligne 2 (ex: `Court \n Une phrase extrêmement longue pour tester le recalcul de la largeur maximale`).
2. Passez le statut de ce nœud à `Urgent` 🚨.
3. Ajoutez-lui une URL 🔗 et un chemin de fichier 📄.


* **Résultat attendu :** Le rectangle entourant le nœud (`self.rect`) doit englober parfaitement le texte et **tous** les émojis sans qu'aucun mot ne subisse de retour à la ligne forcé ou ne soit tronqué par les bords droits/gauches.

---

### 🧪 Test 3 : L'alignement chirurgical des Flèches sur le Losange (`diamond`)

* **Objectif :** Valider que la dichotomie à 100 pas intercepte correctement les coins obliques.
* **Actions :**
1. Créez un nœud avec la forme `diamond` (Losange) et un autre avec la forme `box`. Connectez-les.
2. Faites tourner lentement le nœud `box` autour du losange à $360^\circ$ (en le déplaçant à la souris).
3. Observez l'endroit précis où la pointe de la flèche de la branche touche le losange.


* **Résultat attendu :** La pointe de la flèche doit flouter et suivre la ligne brisée du losange au pixel près. Elle ne doit **jamais flotter dans le vide** à l'extérieur, ni **pénétrer à l'intérieur** de la couleur de fond du losange.

---

### 🧪 Test 4 : La sélection d'une branche courbe "au pixel près" (`shape`)

* **Objectif :** S'assurer que le `QPainterPathStroker` de 20 pixels de large permet d'attraper facilement une liaison sans forcer l'utilisateur à viser au millimètre.
* **Actions :**
1. Créez une liaison très courbée (`line_routing_mode = 'curved'`) entre deux nœuds éloignés.
2. Essayez de cliquer sur la branche en positionnant votre curseur de souris légèrement à côté de la ligne (à environ 5-8 pixels de distance de la courbe visible).


* **Résultat attendu :** La liaison doit passer en surbrillance bleue (`#4A90E2`) et s'épaissir. Grâce à votre méthode `shape()`, la zone de détection de clic est élargie, rendant la sélection confortable.

---

### 🧪 Test 5 : Le comportement du Magnétisme (`Snap to Grid`) en diagonale

* **Objectif :** Vérifier que les signaux de géométrie se coupent et s'activent proprement lors de la réévaluation des coordonnées.
* **Actions :**
1. Activez le snap-to-grid.
2. Déplacez un nœud très lentement en diagonale.


* **Résultat attendu :** Le nœud doit faire de légers "bonds" visuels de 20 pixels en 20 pixels. La ligne connectée à ce nœud ne doit pas afficher de saccades ou de retard d'affichage : elle doit se mettre à jour de manière fluide et synchrone avec le mouvement saccadé du nœud.

