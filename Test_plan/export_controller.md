## Cas de Test 1 : Protection face à un espace vide
Action : Ouvrez un onglet vierge (aucun nœud présent) ou supprimez tous les nœuds, puis lancez successivement l'exportation PNG, PDF et Markdown.
Résultat attendu : L'application ne doit pas crasher. Pour chaque format, une boîte de dialogue d'alerte (QMessageBox) s'affiche pour vous indiquer que la carte est vide et l'opération s'interrompt proprement.

## Cas de Test 2 : Exportation PNG et intégrité visuelle
Action : Ajoutez quelques nœuds étalés horizontalement, appliquez-leur des textes et des couleurs. Lancez l'export PNG. Enregistrez-le sous le nom test_export.png.
Résultat attendu : * Vos sélections en cours ne doivent pas apparaître (pas de bordure de focus sur l'image finale).

Ouvrez le fichier PNG généré : l'image doit être parfaitement nette, centrée sur un fond gris très clair (#f8f9fa) avec une marge uniforme de sécurité de 50 pixels tout autour de vos éléments les plus excentrés.

## Cas de Test 3 : Exportation PDF et mise en page dynamique (A4)
Action 3.1 : Créez une carte mentale très large (plus large que haute) et lancez l'export PDF.
Résultat attendu : Ouvrez le PDF, la feuille est automatiquement configurée en mode Paysage (Landscape) pour épouser la forme de votre travail. Tout est centré.

Action 3.2 : Créez une carte mentale très étirée verticalement et lancez l'export PDF.
Résultat attendu : Le PDF s'adapte et passe automatiquement en mode Portrait. La mindmap est réduite proportionnellement pour s'afficher entièrement sur une seule page A4 sans déborder.

## Cas de Test 4 : Exportation Markdown et contrôle sémantique
Action : Créez un nœud Racine, donnez-lui un enfant (Nœud A) doté d'une URL, et un sous-enfant (Nœud B) doté d'un fichier joint. Lancez l'exportation Markdown (.md). Ouvrez le fichier avec un éditeur de texte.
Résultat attendu : * L'arborescence par indentation d'espaces doit être respectée.
Le document doit afficher exactement ceci :

Plaintext
- Racine
  - Nœud A (URL: https://...)
    - Nœud B (Fichier: .mindmap_attachments/...)