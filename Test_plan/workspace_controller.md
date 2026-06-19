🧪 Test 1 : Anti-destruction d'onglets non sauvés
Actions :

Lancez l'application. Modifiez le document en cours pour faire apparaître l'étoile (*).

Cliquez sur le bouton pour Créer une nouvelle workspace ou Charger une workspace.

Dans la boîte de dialogue de fermeture qui surgit, cliquez sur Annuler (Cancel).

Résultat attendu : L'opération s'arrête net. L'explorateur de fichiers de sauvegarde .mindy ne doit même pas s'ouvrir. Votre onglet non enregistré est préservé.

🧪 Test 2 : La mise à jour du compteur dynamique
Actions :

Créez un nouvel espace de travail nommé Demo.mindy.

Ouvrez deux cartes JSON enregistrées sur votre disque.

Cliquez sur le bouton d'ajout à la Workspace pour la première carte, puis pour la deuxième.

Résultat attendu : Le label en haut ou dans votre barre d'outils doit s'actualiser en temps réel et afficher : 📁 Workspace : Demo.mindy (2 cartes) avec le 's' du pluriel appliqué correctement.

🧪 Test 3 : Retrait et fermeture synchrone
Actions :

Dans une workspace active contenant plusieurs cartes, sélectionnez l'onglet d'une carte faisant partie de cette session.

Cliquez sur le bouton permettant de retirer la carte de la workspace.

Résultat attendu : Non seulement la carte disparaît de l'index du fichier .mindy sur le disque, mais l'onglet se ferme instantanément à l'écran, vous laissant sur un environnement de travail propre.