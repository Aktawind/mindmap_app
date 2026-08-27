import os
import sys
import json

MANIFEST_FILENAME = "manifest.json"

# Noms affichés historiques des templates fournis avec l'application (avant l'introduction du manifeste).
DEFAULT_DISPLAY_NAMES = {
    "cadrage_idee.json": "🎯 Cadrage d'Idée",
    "resolution_probleme.json": "🔍 Résolution de Problème",
    "gestion_temps.json": "⏳ Organisation des priorités",
    "brain_dump.json": "🧠 Brain Dump",
    "onboarding_technique.json": "🚀 Onboarding Technique",
    "hub_passions.json": "🎨 Hub Multi-Passions",
    "organisation_voyage.json": "✈️ Organisation d'un Voyage",
    "preparation_reunion.json": "🗣️ Préparation Réunion",
    "retro_projet.json": "🏁 Rétrospective de Fin de Projet",
    "daily_capsule.json": "☀️ Daily Capsule",
    "sante_mentale_energie.json": "🔋 Santé Mentale et Énergie",
    "urgence_colere.json": "🚨 Urgence Colère",
}


def resource_path(relative_path):
    """Calcule le chemin absolu vers les ressources (gère l'exécutable PyInstaller)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
    return os.path.join(base_path, relative_path)


def get_templates_dir():
    path = resource_path("templates")
    os.makedirs(path, exist_ok=True)
    return path


def _manifest_path():
    return os.path.join(get_templates_dir(), MANIFEST_FILENAME)


def load_manifest():
    """Charge le mapping fichier -> nom affiché, en le synchronisant avec les fichiers réellement présents."""
    path = _manifest_path()
    manifest = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    changed = False
    templates_dir = get_templates_dir()
    for filename in os.listdir(templates_dir):
        if not filename.endswith(".json") or filename == MANIFEST_FILENAME:
            continue
        if filename not in manifest:
            manifest[filename] = DEFAULT_DISPLAY_NAMES.get(
                filename, os.path.splitext(filename)[0].replace('_', ' ').title()
            )
            changed = True

    # Purge des entrées dont le fichier a disparu (suppression manuelle sur le disque)
    for filename in list(manifest.keys()):
        if not os.path.exists(os.path.join(templates_dir, filename)):
            del manifest[filename]
            changed = True

    if changed:
        save_manifest(manifest)

    return manifest


def save_manifest(manifest):
    try:
        with open(_manifest_path(), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du manifeste des templates : {e}")


def list_templates():
    """Retourne la liste triée par nom des templates disponibles, sous forme de tuples (filename, display_name)."""
    manifest = load_manifest()
    return sorted(manifest.items(), key=lambda item: item[1].lower())


def _slugify(display_name):
    slug = "".join(c if c.isalnum() else "_" for c in display_name.strip().lower()).strip("_")
    return slug or "template"


def add_template_from_state(display_name, root_tree_data):
    """Crée un nouveau fichier de template à partir d'un arbre de nœuds sérialisé (format 'root' + cross_links)."""
    templates_dir = get_templates_dir()

    slug = _slugify(display_name)
    filename = f"{slug}.json"
    counter = 1
    while os.path.exists(os.path.join(templates_dir, filename)):
        filename = f"{slug}_{counter}.json"
        counter += 1

    with open(os.path.join(templates_dir, filename), "w", encoding="utf-8") as f:
        json.dump(root_tree_data, f, indent=2, ensure_ascii=False)

    manifest = load_manifest()
    manifest[filename] = display_name
    save_manifest(manifest)
    return filename


def update_template_content(filename, root_tree_data):
    """Écrase le contenu d'un template existant."""
    path = os.path.join(get_templates_dir(), filename)
    if not os.path.exists(path):
        return False
    with open(path, "w", encoding="utf-8") as f:
        json.dump(root_tree_data, f, indent=2, ensure_ascii=False)
    return True


def rename_template(filename, new_display_name):
    manifest = load_manifest()
    if filename not in manifest:
        return False
    manifest[filename] = new_display_name
    save_manifest(manifest)
    return True


def delete_template(filename):
    path = os.path.join(get_templates_dir(), filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Erreur lors de la suppression du template : {e}")
        return False

    manifest = load_manifest()
    if filename in manifest:
        del manifest[filename]
        save_manifest(manifest)
    return True


def refresh_template_combo(app_window):
    """Repeuple dynamiquement la liste déroulante des templates de la toolbar."""
    combo = getattr(app_window, 'template_combo', None)
    if combo is None:
        return

    combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem("Choisir un template...")
        for filename, display_name in list_templates():
            combo.addItem(display_name, filename)
        combo.setCurrentIndex(0)
    finally:
        combo.blockSignals(False)
