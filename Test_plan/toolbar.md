🧪 Test 1 : Persistance Visuelle et Mécanique des Boutons à Bascule (Toggle)
Actions :

Lance l'application.

Clique sur le bouton "🧲 Aimant Grille" puis sur "Liens courbes".

Déplace un nœud sur ton canevas graphique pour vérifier que la grille et l'aimantage s'activent.

Résultat attendu :

Le bouton "🧲 Aimant Grille" doit changer de style visuel de façon permanente (fond bleu vif, texte blanc).

Le bouton "Liens courbes" doit lui aussi rester enfoncé ou changer de style (fond vert ou bleu selon ta charte).

Si tu recliques dessus, ils reprennent instantanément leur couleur neutre initiale (blanc/gris clair).

🧪 Test 2 : Positionnement du Bouton "➕ Ajouter un onglet"
Actions :

Redimensionne la fenêtre principale de ton application de gauche à droite (étire-la et rétrécis-la).

Clique sur le bouton "➕ Ajouter un onglet" à plusieurs reprises.

Résultat attendu :

Le bouton ne doit pas bouger avec la barre d'outils, il doit rester ancré strictement tout à droite de la barre d'onglets (QTabWidget).

Chaque clic doit ouvrir un nouvel onglet vierge de manière fluide sans décalage d'interface.

🧪 Test 3 : Application et réinitialisation d'un modèle (Template)
Actions :

Ouvre un onglet vierge.

Clique sur le menu déroulant des templates et sélectionne "🎯 Cadrage d'Idée".

Une fois la carte générée, reclique sur le menu déroulant.

Résultat attendu :

La structure du Mind Map correspondante doit se dessiner automatiquement sur le graphique actuel.

Aucun crash de type IndexError ou AttributeError ne doit survenir lors du traitement du signal généré par l'index.

🧪 Test 1 : Alignement instantané du mode de routage à la création
Actions :

Lance l'application.

Assure-toi que le bouton "Liens courbes" n'est pas activé (mode liens droits).

Sélectionne un nœud existant (le nœud central par exemple) et appuie sur la touche Tab de ton clavier pour générer une sous-idée.

Résultat attendu :

Le nouveau lien doit apparaître sous forme d'une ligne parfaitement droite dès sa naissance à l'écran. Il ne doit pas y avoir besoin de secouer ou déplacer le nœud pour qu'il s'aligne.

🧪 Test 2 : Connexion manuelle à la volée (Bouton Relier)
Actions :

Crée deux nœuds isolés sur ton canevas.

Laisse le bouton "Liens courbes" désactivé.

Sélectionne les deux nœuds (via Ctrl + Clic), puis clique sur le bouton bleu "Relier les nœuds".

Résultat attendu :

Le lien manuel créé pour connecter les deux entités doit être instantanément rectiligne/droit.