"""Sélecteur d'emojis intégré, pour en ajouter rapidement au texte d'un nœud.

Les emojis sont du simple texte, affiché en couleur par la police emoji de Windows (Segoe UI
Emoji) : aucune bibliothèque ni image à embarquer. Les drapeaux sont volontairement absents,
Windows les affichant comme deux lettres plutôt que comme un drapeau.
"""
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLineEdit, QLabel, QScrollArea, QWidget, QToolButton
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from ui import theme

COLUMNS = 10
MAX_RECENTS = COLUMNS * 2

# (catégorie, [(emoji, mots-clés pour la recherche)])
EMOJI_CATEGORIES = [
    ("Smileys", [
        ("😀", "sourire content joie"), ("😃", "sourire heureux"), ("😄", "rire sourire"),
        ("😁", "grand sourire"), ("😆", "rire mort de rire"), ("😅", "sueur soulagement gêne"),
        ("😂", "pleurer de rire mdr"), ("🙂", "sourire léger"), ("😉", "clin d'oeil"),
        ("😊", "rougir content timide"), ("😇", "ange innocent"), ("🥰", "amour coeurs"),
        ("😍", "amoureux yeux coeur"), ("🤩", "étoiles émerveillé"), ("😘", "bisou"),
        ("😋", "miam délicieux"), ("😎", "cool lunettes"), ("🤓", "intello geek"),
        ("🤔", "réfléchir penser question"), ("🤨", "sceptique doute"), ("😐", "neutre"),
        ("😑", "blasé"), ("😶", "sans voix muet"), ("🙄", "lever les yeux agacé"),
        ("😏", "malin narquois"), ("😬", "grimace gêne oups"), ("😌", "soulagé serein calme"),
        ("😔", "pensif déçu"), ("😴", "dormir sommeil fatigue"), ("🤒", "malade fièvre"),
        ("🤯", "esprit explosé choqué"), ("🥳", "fête anniversaire"), ("😕", "confus perplexe"),
        ("😟", "inquiet souci"), ("😮", "surpris étonné"), ("😲", "stupéfait"),
        ("😳", "gêné rougir"), ("🥺", "supplier"), ("😢", "triste larme"),
        ("😭", "pleurer sanglot"), ("😱", "peur horreur cri"), ("😤", "frustré énervé"),
        ("😡", "colère rage fâché"), ("🤬", "insulte furieux"), ("🥵", "chaud"),
        ("🥶", "froid gelé"), ("😵", "étourdi"), ("🤗", "câlin accueil"),
        ("🤫", "chut secret silence"), ("🤐", "bouche cousue secret"),
    ]),
    ("Gestes et personnes", [
        ("👍", "pouce ok d'accord valider oui"), ("👎", "pouce bas non refuser"),
        ("👌", "ok parfait"), ("✌️", "victoire paix"), ("🤞", "croiser les doigts chance"),
        ("👏", "applaudir bravo"), ("🙌", "hourra célébrer"), ("🙏", "merci prière s'il vous plaît"),
        ("🤝", "poignée de main accord partenariat"), ("👋", "salut bonjour au revoir"),
        ("✋", "stop main levée"), ("👉", "pointer droite"), ("👈", "pointer gauche"),
        ("👆", "pointer haut"), ("👇", "pointer bas"), ("☝️", "important un"),
        ("💪", "force muscle motivation"), ("🧠", "cerveau idée réflexion"), ("👀", "yeux regarder voir"),
        ("👂", "oreille écouter"), ("🗣️", "parler voix"), ("👤", "personne utilisateur"),
        ("👥", "groupe équipe personnes"), ("🧑‍💻", "développeur informaticien ordinateur"),
        ("👨‍👩‍👧", "famille"), ("🧑‍🏫", "professeur formateur"), ("🧑‍💼", "employé bureau manager"),
        ("🏃", "courir sport rapide"), ("🧘", "méditation zen yoga calme"), ("🙋", "question lever la main"),
        ("🤷", "je ne sais pas hausser les épaules"), ("🙅", "non interdit"), ("💁", "information"),
    ]),
    ("Travail et objets", [
        ("📌", "épingle punaise important"), ("📍", "lieu position repère"), ("📎", "trombone pièce jointe"),
        ("📝", "note écrire mémo"), ("✏️", "crayon écrire modifier"), ("🖊️", "stylo"),
        ("📒", "carnet"), ("📓", "cahier"), ("📚", "livres apprendre étudier"),
        ("📖", "livre lire"), ("📄", "document page fichier"), ("📑", "onglets documents"),
        ("📁", "dossier"), ("📂", "dossier ouvert"), ("🗂️", "classeur ranger"),
        ("📋", "presse-papier liste checklist"), ("📅", "calendrier date"), ("📆", "agenda planning"),
        ("🗓️", "calendrier spirale"), ("⏰", "réveil alarme heure"), ("⏳", "sablier attente en cours"),
        ("⌛", "sablier fini temps"), ("⏱️", "chronomètre durée"), ("📊", "graphique barres statistiques"),
        ("📈", "hausse croissance progression"), ("📉", "baisse diminution"), ("💼", "mallette travail business"),
        ("💻", "ordinateur portable pc"), ("🖥️", "écran ordinateur"), ("⌨️", "clavier"),
        ("🖱️", "souris"), ("📱", "téléphone mobile smartphone"), ("☎️", "téléphone appel"),
        ("📧", "email courriel mail"), ("✉️", "enveloppe lettre courrier"), ("📬", "boîte aux lettres"),
        ("📢", "annonce haut-parleur communication"), ("🔔", "cloche notification rappel"),
        ("🔍", "loupe chercher recherche"), ("🔑", "clé accès mot de passe"), ("🔒", "cadenas verrouillé sécurité"),
        ("🔓", "déverrouillé ouvert"), ("🛠️", "outils réparer"), ("🔧", "clé à molette réglage"),
        ("⚙️", "engrenage paramètres réglages"), ("🧰", "boîte à outils"), ("🔗", "lien chaîne url"),
        ("💡", "idée ampoule astuce"), ("🔋", "batterie énergie"), ("🧪", "test expérience labo"),
        ("🧩", "puzzle pièce module"), ("🎯", "cible objectif but"), ("🏆", "trophée victoire réussite"),
        ("🥇", "médaille premier or"), ("💰", "argent budget sac"), ("💶", "euro billet argent"),
        ("💳", "carte bancaire paiement"), ("🛒", "caddie courses achat"), ("🎁", "cadeau"),
        ("📦", "colis paquet livraison"), ("🗑️", "poubelle supprimer"), ("🏠", "maison domicile"),
        ("🏢", "bureau entreprise immeuble"), ("🏥", "hôpital santé"), ("🏫", "école"),
    ]),
    ("Symboles", [
        ("✅", "valider fait terminé coche"), ("☑️", "case cochée"), ("✔️", "coche ok"),
        ("❌", "croix erreur annuler non"), ("❎", "croix bouton"), ("⚠️", "attention avertissement danger"),
        ("🚨", "urgent alerte gyrophare"), ("⛔", "interdit sens interdit"), ("🚫", "interdit défendu"),
        ("❓", "question"), ("❗", "exclamation important"), ("‼️", "double exclamation"),
        ("⭐", "étoile favori"), ("🌟", "étoile brillante"), ("✨", "étincelles nouveau magie"),
        ("🔥", "feu urgent tendance"), ("💥", "explosion choc"), ("💯", "cent parfait"),
        ("❤️", "coeur rouge amour"), ("🧡", "coeur orange"), ("💛", "coeur jaune"),
        ("💚", "coeur vert"), ("💙", "coeur bleu"), ("💜", "coeur violet"),
        ("🖤", "coeur noir"), ("🤍", "coeur blanc"), ("💔", "coeur brisé"),
        ("🔴", "rond rouge"), ("🟠", "rond orange"), ("🟡", "rond jaune"),
        ("🟢", "rond vert"), ("🔵", "rond bleu"), ("🟣", "rond violet"),
        ("⚫", "rond noir"), ("⚪", "rond blanc"), ("🟥", "carré rouge"),
        ("🟧", "carré orange"), ("🟨", "carré jaune"), ("🟩", "carré vert"),
        ("🟦", "carré bleu"), ("🟪", "carré violet"), ("➡️", "flèche droite suivant"),
        ("⬅️", "flèche gauche précédent"), ("⬆️", "flèche haut"), ("⬇️", "flèche bas"),
        ("↗️", "flèche diagonale hausse"), ("🔄", "rafraîchir répéter cycle"), ("🔁", "boucle répéter"),
        ("➕", "plus ajouter"), ("➖", "moins retirer"), ("✖️", "multiplier"),
        ("➗", "diviser"), ("🟰", "égal"), ("♻️", "recycler"),
        ("1️⃣", "un premier"), ("2️⃣", "deux deuxième"), ("3️⃣", "trois troisième"),
        ("4️⃣", "quatre"), ("5️⃣", "cinq"), ("🆕", "nouveau new"),
        ("🆗", "ok"), ("🆘", "sos aide"), ("ℹ️", "information info"),
    ]),
    ("Nature et météo", [
        ("☀️", "soleil beau temps"), ("🌤️", "soleil nuage"), ("☁️", "nuage"),
        ("🌧️", "pluie"), ("⛈️", "orage"), ("❄️", "neige flocon froid"),
        ("🌈", "arc-en-ciel"), ("⚡", "éclair énergie rapide"), ("💧", "goutte eau"),
        ("🌊", "vague mer océan"), ("🌙", "lune nuit"), ("🌍", "terre monde planète europe"),
        ("🌱", "pousse plante croissance début"), ("🌳", "arbre"), ("🌲", "sapin"),
        ("🍀", "trèfle chance"), ("🌸", "fleur cerisier"), ("🌻", "tournesol"),
        ("🌹", "rose"), ("🍂", "feuilles automne"), ("🐶", "chien"),
        ("🐱", "chat"), ("🐻", "ours"), ("🦊", "renard"),
        ("🐝", "abeille travail"), ("🦋", "papillon"), ("🐢", "tortue lent"),
        ("🐌", "escargot lent"), ("🦉", "chouette hibou sagesse"), ("🐞", "coccinelle bug"),
    ]),
    ("Nourriture", [
        ("☕", "café pause"), ("🍵", "thé"), ("🍺", "bière"),
        ("🍷", "vin"), ("🥂", "trinquer champagne fête"), ("🍎", "pomme"),
        ("🍌", "banane"), ("🍓", "fraise"), ("🥑", "avocat"),
        ("🥕", "carotte"), ("🍞", "pain"), ("🥐", "croissant"),
        ("🧀", "fromage"), ("🍕", "pizza"), ("🍔", "burger"),
        ("🍟", "frites"), ("🥗", "salade"), ("🍝", "pâtes"),
        ("🍰", "gâteau"), ("🎂", "anniversaire gâteau"), ("🍫", "chocolat"),
        ("🍿", "popcorn"), ("🍽️", "repas assiette restaurant"), ("🥤", "boisson"),
    ]),
    ("Activités et voyages", [
        ("🎉", "fête célébration bravo"), ("🎊", "confettis"), ("🎈", "ballon"),
        ("🎨", "art peinture créativité"), ("🎵", "musique note"), ("🎧", "casque écouter musique"),
        ("🎬", "film cinéma"), ("📷", "photo appareil"), ("🎮", "jeu vidéo"),
        ("🎲", "dé jeu hasard"), ("♟️", "échecs stratégie"), ("⚽", "football sport"),
        ("🏀", "basket"), ("🎾", "tennis"), ("🚴", "vélo"),
        ("🏋️", "musculation sport"), ("🏊", "natation"), ("⛰️", "montagne"),
        ("🏖️", "plage vacances"), ("🏕️", "camping"), ("✈️", "avion voyage vol"),
        ("🚗", "voiture"), ("🚆", "train"), ("🚌", "bus"),
        ("🚲", "vélo bicyclette"), ("🚀", "fusée lancement démarrage projet"), ("🗺️", "carte plan"),
        ("🧭", "boussole direction"), ("🏁", "drapeau arrivée fin"), ("🧳", "valise bagage"),
    ]),
]


class EmojiPickerDialog(QDialog):
    """Petite fenêtre de choix d'emoji : recherche par mot-clé (en français), emojis
    récemment utilisés en tête, puis toutes les catégories. Un clic choisit et ferme."""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Insérer un emoji")
        self.resize(460, 440)
        self._settings = settings
        self.selected_emoji = None
        self._palette = theme.get_palette(parent)

        layout = QVBoxLayout(self)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Rechercher (ex : idée, valider, urgent, café...)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._rebuild)
        self.search.returnPressed.connect(self._pick_first_result)
        layout.addWidget(self.search)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self._first_result = None
        self._rebuild()
        self.search.setFocus()

    def _load_recents(self):
        if self._settings is None:
            return []
        try:
            recents = json.loads(self._settings.value("recent_emojis", "[]"))
        except (TypeError, ValueError):
            return []
        return [e for e in recents if isinstance(e, str)] if isinstance(recents, list) else []

    def _remember(self, emoji):
        if self._settings is None:
            return
        recents = [e for e in self._load_recents() if e != emoji]
        recents.insert(0, emoji)
        self._settings.setValue("recent_emojis", json.dumps(recents[:MAX_RECENTS], ensure_ascii=False))

    def _rebuild(self):
        query = self.search.text().strip().lower()
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(6)
        self._first_result = None

        sections = []
        if not query:
            recents = self._load_recents()
            if recents:
                sections.append(("Récents", recents))
        for title, entries in EMOJI_CATEGORIES:
            matches = [e for e, keywords in entries if not query or query in keywords or query in title.lower()]
            if matches:
                sections.append((title, matches))

        if not sections:
            empty = QLabel("Aucun emoji ne correspond à cette recherche.", container)
            empty.setStyleSheet(f"color: {self._palette['text_muted']};")
            v.addWidget(empty)

        emoji_font = QFont("Segoe UI Emoji", 16)
        button_style = (
            f"QToolButton {{ border: none; border-radius: 6px; background: transparent; }}"
            f"QToolButton:hover {{ background: {self._palette['bg_hover']}; }}"
        )
        for title, emojis in sections:
            header = QLabel(title, container)
            header.setStyleSheet(f"color: {self._palette['text_muted']}; font-weight: bold; font-size: 11px;")
            v.addWidget(header)
            grid_widget = QWidget(container)
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(2)
            for i, emoji in enumerate(emojis):
                btn = QToolButton(grid_widget)
                btn.setText(emoji)
                btn.setFont(emoji_font)
                btn.setFixedSize(38, 38)
                btn.setStyleSheet(button_style)
                btn.setAutoRaise(True)
                btn.clicked.connect(lambda _, e=emoji: self._choose(e))
                grid.addWidget(btn, *divmod(i, COLUMNS))
                if self._first_result is None:
                    self._first_result = emoji
            grid.setColumnStretch(COLUMNS, 1)
            v.addWidget(grid_widget)
        v.addStretch()
        self.scroll.setWidget(container)

    def _pick_first_result(self):
        if self._first_result:
            self._choose(self._first_result)

    def _choose(self, emoji):
        self.selected_emoji = emoji
        self._remember(emoji)
        self.accept()


def pick_emoji(app_window):
    """Ouvre le sélecteur et renvoie l'emoji choisi (ou None si annulé)."""
    dialog = EmojiPickerDialog(app_window, getattr(app_window, 'settings', None))
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.selected_emoji
    return None
