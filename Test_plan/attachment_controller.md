## Protocole de Test Manuel : Gestion des Pièces Jointes et Liens

> ⚠️ **Prérequis avant de commencer :** > 1. Lancez votre application.
> 2. Créez une nouvelle Mind Map et créez au moins deux nœuds (Nœud A et Nœud B).
> 3. Préparez un fichier de test sur votre ordinateur (par exemple un document `test.pdf` ou `photo.png`).

---

### Cas de Test 1 : Sécurité avant sauvegarde (Blocage initial)

* **Action :** Sélectionnez le Nœud A (sur une carte **non encore enregistrée** sur votre disque) et tentez d'ajouter un fichier
* **Résultat attendu :** * Un message d'information s'affiche : *"Veuillez d'abord enregistrer votre Mind Map..."*.

---

### Cas de Test 2 : Attachement et copie locale d'un fichier

* **Action :** La carte étant maintenant sauvegardée, sélectionnez le Nœud A et lancez l'ajout de fichier. Choisissez votre fichier `test.pdf`.
* **Résultat attendu :**
* Le nœud se met à jour visuellement (sa taille se recalcule pour afficher l'indicateur de fichier).
* **Vérification sur votre disque :** Allez dans le dossier où vous avez enregistré `ma_carte.json`. Un dossier caché nommé `.mindmap_attachments` doit avoir été créé. À l'intérieur, vous devez trouver un fichier renommé sous la forme `file_[ID_DU_NOEUD].pdf`.

---

### Cas de Test 3 : Ouverture du fichier joint

* **Action :** Sélectionnez le Nœud A (qui possède le fichier joint) et déclenchez l'action d'ouverture (associée à `open_file`).
* **Résultat attendu :** * Votre lecteur PDF ou logiciel par défaut s'ouvre instantanément et affiche le fichier qui est stocké dans `.mindmap_attachments`.

---

### Cas de Test 4 : Remplacement d'un fichier joint (Nettoyage automatique)

* **Action :** Laissez le Nœud A sélectionné. Relancez l'ajout d'un fichier et choisissez un *autre* fichier (ex: `image.png`).
* **Résultat attendu :**
* Le nœud met à jour ses informations.
* **Vérification sur votre disque :** Dans le dossier `.mindmap_attachments`, l'ancien fichier `file_[ID_DU_NOEUD].pdf` doit avoir **disparu** (supprimé proprement pour ne pas accumuler de fichiers inutiles) et être remplacé par `file_[ID_DU_NOEUD].png`.

---

### Cas de Test 5 : Association et formatage automatique d'une URL

* **Action :** Sélectionnez le Nœud B. Déclenchez l'action d'ajout d'URL (`attach_url`). Dans la boîte de dialogue, tapez simplement `github.com` (sans mettre `https://`). Validez.
* **Résultat attendu :**
* Le nœud B se met à jour graphiquement pour indiquer la présence d'un lien.

---

### Cas de Test 6 : Ouverture de l'URL et bascule automatique (Fallback)

* **Action 6.1 :** Sélectionnez le Nœud B et déclenchez l'action d'ouverture d'URL (`open_url`).
* **Résultat attendu :** Votre navigateur internet par défaut s'ouvre et charge la page `https://github.com` (le contrôleur a corrigé le protocole manquant).


* **Action 6.2 (Le test du bug corrigé) :** Sélectionnez le Nœud B (qui n'a *que* une URL et *aucun* fichier) et déclenchez cette fois l'action d'ouverture de **fichier** (`open_file`).
* **Résultat attendu :** L'application ne plante pas. Elle détecte l'absence de fichier, bascule sur la fonction URL, et ouvre votre navigateur internet vers le lien du nœud.

---

### Cas de Test 7 : Suppression complète (Détachement)

* **Action :** Sélectionnez le Nœud A (qui contient votre image/fichier). Déclenchez l'action pour détacher les liens (`detach_links`).
* **Résultat attendu :**
* Le nœud A redevient un nœud normal visuellement.
* **Vérification sur votre disque :** Le fichier correspondant dans le dossier `.mindmap_attachments` a été définitivement supprimé.