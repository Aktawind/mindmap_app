🧪 Test 1 : Le test du "Rond-Point" (Références Circulaires)
Pourquoi c'est critique : C'est le piège absolu des sérialiseurs de cartes mentales. Si le Nœud A pointe vers le Nœud B, et que le Nœud B repointe vers le Nœud A, un sérialiseur mal conçu va boucler à l'infini et faire crasher l'application (RecursionError) lors de la sauvegarde.

Actions :

Créez un Nœud A et un Nœud B.

Créez une liaison allant de A vers B.

Créez une deuxième liaison allant de B vers A (ou une liaison de A vers lui-même).

Sauvegardez le projet (Ctrl + S), fermez l'onglet, puis rechargez le fichier.

Résultat attendu : L'application doit sauvegarder instantanément sans geler. Au rechargement, les deux flèches doivent être présentes, bien orientées, sans doublons ni morceaux manquants.

🧪 Test 2 : Le décodage d'un JSON externe "altéré" (Sécurité)
Pourquoi c'est critique : Que se passe-t-il si un utilisateur modifie son fichier .json à la main ou si un fichier est partiellement corrompu ? Le sérialiseur doit rejeter les données proprement au lieu de casser l'UI.

Actions :

Créez une petite Mind Map, sauvegardez-la sous test_crash.json et ouvrez ce fichier dans un éditeur de texte (Bloc-notes / VS Code).

Modifiez une valeur clé pour injecter une anomalie (par exemple, remplacez la valeur de position "x": 150 par une chaîne de caractères "x": "cent-cinquante", ou supprimez la clé "global_line_routing").

Essayez de charger ce fichier dans votre application.

Résultat attendu : L'application ne doit pas afficher un écran blanc ou un canevas à moitié cassé. Elle doit soit intercepter l'erreur via un try/except dans apply_state et afficher un QMessageBox.critical, soit appliquer des valeurs par défaut sécurisées (ex: si x est invalide, positionner le nœud à 0).

🧪 Test 3 : L'intégrité des ID au copier-coller ou clonage
Pourquoi c'est critique : Si le sérialiseur génère ou charge des identifiants de nœuds (node_id), ils doivent être uniques. Si deux nœuds possèdent le même ID après une sauvegarde/lecture, dessiner une nouvelle branche va rendre l'application folle (les lignes vont se lier au mauvais nœud).

Actions :

Créez une structure (Nœud A connecté au Nœud B). Sauvegardez.

Inspectez le fichier JSON généré.

Résultat attendu : Vérifiez que chaque entrée dans la table des liaisons (edges ou lines) fait référence à des ID de nœuds sources et destinations qui existent bel et bien dans la liste des nœuds (nodes). Aucun ID ne doit être dupliqué.

🧪 Test 4 : La persistence des styles personnalisés (Stress-Test Visuel)
Pourquoi c'est critique : Le sérialiseur ne doit pas seulement sauvegarder la structure (les textes), il doit figer l'exacte signature visuelle de la carte.

Actions :

Créez une carte en appliquant un maximum de configurations différentes sur vos composants :

Un nœud en forme de Losange (diamond), fond Vert, texte en Gras.

Un nœud en forme d'Ellipse, fond Rouge, statut Urgent 🚨 avec un lien URL attaché.

Une liaison en mode orthogonal et une autre en mode curved.

Sauvegardez, fermez l'application, et relancez-la.

Résultat attendu : Au démarrage, la carte doit être strictement identique au pixel près. Si le losange est redevenu un rectangle ou si le mode orthogonal a sauté pour redevenir courbe, c'est que votre sérialiseur oublie d'extraire ou d'injecter ces propriétés spécifiques dans le dictionnaire d'état.