🧪 Test 1 : L'immunité du "Coller" à froid
Objectif : Vérifier que l'application ne crash pas si on tente de coller sans avoir rien copié au préalable.

Actions :

Démarrez l'application (sur un projet vierge).

Faites immédiatement la combinaison de touches Ctrl + V (ou cliquez sur le bouton Coller si vous en avez un).

Résultat attendu : Rien ne doit se passer. Aucun nœud ne doit apparaître, mais surtout, l'application ne doit pas se fermer ni freezer, et aucun message d'erreur de type AttributeError ne doit être imprimé dans votre console.

🧪 Test 2 : La duplication et l'anti-collision d'ID
Objectif : S'assurer que le copier-coller fonctionne et que le nœud dupliqué possède un identifiant unique indépendant.

Actions :

Créez un nœud, changez sa couleur en orange et écrivez "Test ID" dedans.

Sélectionnez-le et faites Ctrl + C.

Faites Ctrl + V.

Résultat attendu : Un deuxième nœud orange "Test ID" apparaît pile au centre de votre écran. Il est automatiquement sélectionné. Déplacez-le, créez une liaison depuis ce nouveau nœud vers un autre : la ligne doit s'attacher correctement. (Si l'ID avait cloné l'ancien, la ligne aurait sauté vers le premier nœud).

🧪 Test 3 : La règle d'or du double-clic (Racine vs Idées)
Objectif : Valider la logique de peuplement automatique de la Mind Map.

Actions :

Ouvrez un onglet complètement vide (sans aucun nœud).

Double-cliquez n'importe où sur le fond de la scène.

Constat 1 : Un nœud bleu nommé "Nouvelle idée centrale" doit apparaître.

Double-cliquez à un autre endroit sur le fond.

Constat 2 : Un nœud beige nommé "Nouvelle idée" doit apparaître.

Résultat attendu : Le premier nœud créé est configuré comme le root (bleu), tandis que tous les clics suivants génèrent des branches secondaires (beiges).

🧪 Test 4 : L'interception de fermeture — Scénario "Annuler"
Objectif : Vérifier que l'utilisateur peut changer d'avis et stopper la fermeture de l'application.

Actions :

Ouvrez deux onglets.

Modifiez le contenu du deuxième onglet pour faire apparaître l'étoile (*).

Cliquez sur la croix rouge (X) en haut à droite de la fenêtre pour fermer l'application.

La boîte de dialogue s'ouvre. Cliquez sur Annuler (Cancel).

Résultat attendu : La boîte de dialogue se ferme et l'application reste entièrement ouverte. L'onglet modifié est toujours présent avec son étoile.

🧪 Test 5 : L'interception de fermeture — Scénario "Sauvegarde avortée"
Objectif : Valider le correctif du parcours inverse si l'utilisateur annule le choix du fichier.

Actions :

Créez un Nouveau Projet (il n'a donc pas de fichier .json associé sur votre disque).

Ajoutez un nœud pour le rendre dirty (*).

Cliquez sur la croix rouge (X) de l'application.

La boîte de dialogue vous demande s'il faut enregistrer. Cliquez sur Oui (Yes).

L'explorateur de fichiers de Windows/Mac s'ouvre pour vous demander où enregistrer le .json. Cliquez sur le bouton Annuler de cet explorateur.

Résultat attendu : L'explorateur se ferme, mais l'application ne doit pas se fermer. Elle doit interrompre sa procédure de fermeture car le fichier n'a pas pu être sauvegardé.