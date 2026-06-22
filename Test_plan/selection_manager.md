🧪 Test 1 : Comportement de la sélection multiple mixte
Actions :

Crée deux nœuds reliés par une branche (Edge).

Avec l'outil de sélection (lasso / rectangle de sélection), englobe les deux nœuds ET la branche en même temps.

Résultat attendu :

La barre de style globale s'affiche.

La section node_controls (formes, couleurs) reste visible car il y a des nœuds dans la sélection.

Le bouton "Relier les nœuds" doit rester caché (car une branche s'est glissée dans la sélection globale, le compte total d'éléments n'est pas strictement égal à 2 nœuds isolés).

🧪 Test 2 : Le commutateur de contexte (Nœud ↔️ Branche)
Actions :

Clique sur un nœud isolé. Observe la barre de style.

Clique directement sur une branche (le lien entre deux nœuds). Observe le changement.

Résultat attendu :

Au clic sur le nœud : Les boutons de fichiers joints, couleurs, et formes sont affichés. La section "Texte de branche" est masquée.

Au clic sur la branche : Les outils du nœud disparaissent instantanément pour laisser place aux options "Texte de branche" et au menu déroulant des flèches. Aucun clignotement ou décalage persistant.

🧪 Test 3 : Détection stricte de la liaison (Bouton "Relier")
Actions :

Maintiens la touche Ctrl enfoncée.

Étape A : Clique sur un premier nœud, puis sur un deuxième nœud.

Étape B : Sans relâcher Ctrl, clique sur un troisième nœud.

Résultat attendu :

Étape A (2 nœuds sélectionnés) : Le bouton bleu "Relier les nœuds" apparaît dans la barre.

Étape B (3 nœuds sélectionnés) : Le bouton bleu disparaît immédiatement.

🧪 Test 4 : Apparition dynamique des boutons d'onglets (Fichier / URL)
Actions :

Crée un nœud vierge et sélectionne-le.

Ajoute un lien URL à ce nœud via le bouton 🔗 URL. Désélectionne le nœud.

Sélectionne à nouveau ce nœud.

Résultat attendu :

Étape 1 : Les boutons 📂 Ouvrir et ❌ Dissocier sont invisibles sur le nœud vierge.

Étape 3 : Dès le clic de sélection sur le nœud contenant l'URL, les boutons 📂 Ouvrir et ❌ Dissocier apparaissent instantanément.