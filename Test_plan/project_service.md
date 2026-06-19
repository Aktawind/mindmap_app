🧪 Test 1 : L'ouverture groupée (Multi-sélection)
Actions :

Cliquez sur le bouton Ouvrir (ou faites le raccourci correspondant).

Dans l'explorateur, maintenez la touche Ctrl enfoncée et sélectionnez 3 fichiers .json différents. Cliquez sur Valider.

Résultat attendu : L'application doit instancier 3 onglets distincts. Le focus final doit se trouver sur le dernier fichier traité, et chaque onglet doit afficher le contenu qui lui correspond sans mélange de données entre les vues.

🧪 Test 2 : Le comportement du premier Undo après ouverture
Actions :

Fermez l'application, puis rouvrez-la (elle recharge le dernier projet modifié automatiquement).

Déplacez un nœud.

Effectuez immédiatement un Ctrl + Z.

Résultat attendu : Le nœud doit retourner à sa place d'origine sans provoquer de plantage. (Grâce à l'harmonisation du format dictionnaire dans undo_stack).

🧪 Test 3 : L'auto-nommage intelligent (Sanitisation du titre)
Actions :

Créez un Nouveau Projet.

Modifiez le nœud racine en écrivant un titre avec des caractères interdits par Windows/Mac pour les noms de fichiers (ex: Rapport: Client? *Urgent*).

Faites Ctrl + S (Enregistrer).

Résultat attendu : La boîte de dialogue s'ouvre en vous suggérant automatiquement le nom Rapport Client Urgent.json. Les caractères :, * et ? ont été nettoyés proprement pour éviter un rejet du système d'exploitation.