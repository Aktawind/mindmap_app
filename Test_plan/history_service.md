## 📋 Plan de Tests Manuels pour le Système d'Historique (Undo/Redo)

### 🧪 Test 1 : La barrière de l'état initial (Anti-Page Blanche)

* **Objectif :** Vérifier que faire un Undo au tout début de la session ne fait pas disparaître le nœud racine ou ne provoque pas un bug visuel.
* **Actions :**
1. Ouvrez un tout nouvel onglet vide.
2. Double-cliquez pour créer le nœud central (`root`).
3. Faites immédiatement **`Ctrl + Z`**.


* **Résultat attendu :** Rien ne doit se passer (le nœud central reste à l'écran). Pourquoi ? Votre code contient la règle de sécurité `if len(workspace.undo_stack) < 2: return None`. L'état d'origine contenant le premier nœud doit être conservé pour éviter que l'utilisateur ne se retrouve bloqué sur un canevas impossible à manipuler.

---

### 🧪 Test 2 : La bifurcation de l'historique (Écrasement du Redo)

* **Objectif :** Valider que le fait de faire une nouvelle action après un Undo nettoie correctement la pile de Redo (pour éviter de pouvoir restaurer des actions du futur qui n'existent plus).
* **Actions :**
1. Créez un nœud A.
2. Créez un nœud B à côté (l'historique contient A, puis A+B).
3. Faites **`Ctrl + Z`**. Le nœud B disparaît (il est envoyé dans la pile `redo_stack`).
4. Au lieu de faire un Redo, créez un **nouveau nœud C**.
5. Essayez maintenant de faire un Redo (**`Ctrl + Y`** ou **`Ctrl + Shift + Z`**).


* **Résultat attendu :** Le raccourci Redo ne doit absolument rien faire. Le nœud B est définitivement perdu, car la création du nœud C a déclenché `workspace.redo_stack.clear()`. C'est le comportement standard et attendu d'un historique.

---

### 🧪 Test 3 : Le filtre anti-doublon (Protection mémoire)

* **Objectif :** S'assurer que le service bloque l'enregistrement si l'état n'a pas bougé (évite de saturer la mémoire RAM).
* **Actions :**
1. Cliquez sur un nœud existant pour le sélectionner.
2. Cliquez frénétiquement plusieurs fois sur ce même nœud sans le déplacer, ou cliquez dans le vide.
3. Faites **`Ctrl + Z`** une seule fois.


* **Résultat attendu :** Le nœud doit immédiatement réagir à l'action *précédente* (par exemple s'effacer ou se déplacer). Si les clics statiques avaient enregistré des états identiques, vous auriez dû faire `Ctrl + Z` autant de fois que vous avez cliqué pour voir un vrai changement à l'écran. Votre garde-fou `== current_state_dict` doit bloquer ces doublons.

---

### 🧪 Test 4 : L'indicateur de modification (`is_dirty`) au retour à l'origine

* **Objectif :** Observer comment se comporte l'étoile de modification (`*`) de l'onglet lors de l'utilisation de l'historique.
* **Actions :**
1. Enregistrez votre projet actuel sur le disque (`Ctrl + S`). L'étoile (`*`) sur l'onglet disparaît.
2. Déplacez un nœud. L'étoile réapparaît (`is_dirty = True`).
3. Faites **`Ctrl + Z`** pour annuler le déplacement.


* **Résultat attendu :** Le nœud revient à sa place. *Note comportementale :* Dans votre code actuel, `workspace.is_dirty = True` est forcé à chaque Undo/Redo. L'étoile restera donc affichée même si vous êtes revenu exactement à l'état sauvegardé. (Pour aller plus loin un jour, il faudrait stocker l'index du dictionnaire qui a été sauvegardé, mais pour l'instant, assurez-vous juste que l'application est bien considérée comme "à sauvegarder").

