"""Fichiers d'une carte (images de nœud, images des notes, fond de canevas, pièces jointes
copiées) et enregistrement des cartes.

Un fichier .mindy est une archive zip qui contient la carte (map.json) et son dossier
.mindmap_attachments : on peut donner un seul fichier, il contient tout. À l'ouverture,
l'archive est extraite dans un dossier de travail de l'application (le « dossier de la
carte »), où sont aussi rangés les fichiers ajoutés ensuite ; l'enregistrement reconstruit
l'archive à partir de ce dossier.

Les anciens .mindy (et les .json) sont du JSON simple, accompagné d'un dossier
.mindmap_attachments placé à côté : ils s'ouvrent toujours, et un .mindy passe au format
archive à son prochain enregistrement.

En mémoire (scène, historique annuler/rétablir), les chemins des images sont absolus pour
que l'affichage fonctionne tel quel ; dans le fichier enregistré, ils sont relatifs au
dossier de la carte. Une carte jamais enregistrée range ses images dans un dossier de
travail de l'application, puis elles sont recopiées dans la carte lors du premier
enregistrement.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from urllib.parse import unquote

from PyQt6.QtCore import QStandardPaths

ATTACHMENTS_DIRNAME = ".mindmap_attachments"
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
MAP_EXTENSIONS = ('.mindy', '.json')
PACKAGE_EXTENSION = '.mindy'
MAP_ENTRY = "map.json"  # la carte, dans l'archive .mindy

_IMG_SRC_RE = re.compile(r'(<img[^>]*\ssrc=")([^"]+)(")', re.IGNORECASE)


def _data_dir(*parts):
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
    return os.path.join(base or os.path.abspath("."), "Mindy", *parts)


def _unsaved_dir():
    return _data_dir("cartes_non_enregistrees", ATTACHMENTS_DIRNAME)


def is_package_path(path):
    return bool(path) and path.lower().endswith(PACKAGE_EXTENSION)


def package_work_dir(map_path):
    """Dossier de travail où est extraite l'archive .mindy `map_path` (un par fichier)."""
    full = os.path.normcase(os.path.abspath(map_path))
    digest = hashlib.sha1(full.encode('utf-8')).hexdigest()[:10]
    name = re.sub(r'[^\w\- ]', '_', os.path.splitext(os.path.basename(map_path))[0])[:40]
    target = _data_dir("cartes_ouvertes", f"{name}_{digest}")
    os.makedirs(target, exist_ok=True)
    return target


def project_dir(ws):
    """Dossier de la carte : celui auquel ses chemins relatifs se rapportent (dossier de
    travail d'une archive .mindy, dossier du fichier pour l'ancien format), ou None pour
    une carte jamais enregistrée."""
    if ws is None:
        return None
    folder = getattr(ws, 'project_dir', None)
    if folder:
        return folder
    file_path = getattr(ws, 'current_file_path', None)
    return os.path.dirname(os.path.abspath(file_path)) if file_path else None


def attachments_dir(ws):
    """Dossier où ranger les images et pièces jointes du workspace (créé au besoin)."""
    folder = project_dir(ws)
    target = os.path.join(folder, ATTACHMENTS_DIRNAME) if folder else _unsaved_dir()
    os.makedirs(target, exist_ok=True)
    return target


def _unique_path(target_dir, base_name):
    name, ext = os.path.splitext(base_name)
    counter = 1
    new_name = base_name
    while os.path.exists(os.path.join(target_dir, new_name)):
        new_name = f"{name}_{counter}{ext}"
        counter += 1
    return os.path.join(target_dir, new_name)


def import_image_file(ws, source_path):
    """Copie une image dans le dossier de la carte et renvoie son chemin absolu."""
    dest_path = _unique_path(attachments_dir(ws), os.path.basename(source_path))
    shutil.copy(source_path, dest_path)
    return dest_path


def save_qimage(ws, image, prefix="note"):
    """Enregistre en PNG une image (ex. presse-papiers) et renvoie son chemin absolu."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = _unique_path(attachments_dir(ws), f"{prefix}_{stamp}.png")
    if not image.save(dest_path, "PNG"):
        raise OSError("échec de l'enregistrement de l'image")
    return dest_path


def note_image_sources(notes):
    """Valeurs src des balises <img> d'une note HTML."""
    if not notes:
        return []
    return [m.group(2) for m in _IMG_SRC_RE.finditer(notes)]


def _same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


# --- Conversion des chemins à l'enregistrement / au chargement ---------------------------

def _iter_nodes(state):
    stack = [state.get("root")] + list(state.get("orphan_nodes") or [])
    while stack:
        node = stack.pop()
        if not node:
            continue
        yield node
        stack.extend(node.get("children") or [])


def _to_relative(path, project_dir, target_dir):
    """Chemin d'image absolu → chemin relatif au dossier de la carte, en recopiant l'image
    dans le dossier de la carte si elle est ailleurs (carte non enregistrée, ancienne
    version qui rangeait les images dans le dossier de lancement, « Enregistrer sous »...)."""
    if not path or not os.path.isabs(path) or not os.path.isfile(path):
        return path
    if not _same_path(os.path.dirname(path), target_dir):
        dest = os.path.join(target_dir, os.path.basename(path))
        if not (os.path.exists(dest) and os.path.getsize(dest) == os.path.getsize(path)):
            dest = _unique_path(target_dir, os.path.basename(path))
            shutil.copy(path, dest)
        path = dest
    return os.path.relpath(path, project_dir).replace('\\', '/')


def _to_absolute(path, project_dir):
    if not path or os.path.isabs(path) or '://' in path:
        return path
    return os.path.normpath(os.path.join(project_dir, path)).replace('\\', '/')


def _map_notes(notes, func):
    if not notes:
        return notes
    return _IMG_SRC_RE.sub(lambda m: m.group(1) + func(m.group(2)) + m.group(3), notes)


def _map_state_paths(state, func):
    state = copy.deepcopy(state)
    if state.get("canvas_image_path"):
        state["canvas_image_path"] = func(state["canvas_image_path"])
    for node in _iter_nodes(state):
        if node.get("image_path"):
            node["image_path"] = func(node["image_path"])
        if node.get("notes"):
            node["notes"] = _map_notes(node["notes"], func)
    return state


def state_for_file(state, project_dir, previous_project_dir=None):
    """Prépare l'état à enregistrer pour le dossier de carte `project_dir` : chemins
    d'images relatifs, images recopiées dans le dossier de la carte. Les pièces jointes
    copiées sont aussi recopiées si le dossier de la carte change (« Enregistrer sous »,
    passage d'un ancien .mindy au format archive...)."""
    target_dir = os.path.join(project_dir, ATTACHMENTS_DIRNAME)
    os.makedirs(target_dir, exist_ok=True)

    def convert(path):
        src = path.replace('/', os.sep) if os.path.isabs(path) else path
        try:
            return _to_relative(src, project_dir, target_dir)
        except OSError as e:
            print(f"Impossible de recopier l'image {path} : {e}")
            return path

    state = _map_state_paths(state, convert)

    if previous_project_dir:
        old_dir = previous_project_dir
        if not _same_path(old_dir, project_dir):
            for node in _iter_nodes(state):
                for att in node.get("attachments") or []:
                    rel = att.get("path")
                    if att.get("type") == "file" and att.get("is_local_copy") and rel and not os.path.isabs(rel):
                        src = os.path.join(old_dir, rel)
                        dest = os.path.join(project_dir, rel)
                        if os.path.isfile(src) and not os.path.exists(dest):
                            try:
                                os.makedirs(os.path.dirname(dest), exist_ok=True)
                                shutil.copy2(src, dest)
                            except OSError as e:
                                print(f"Impossible de recopier la pièce jointe {rel} : {e}")
    return state


def state_from_file(state, project_dir):
    """Inverse de state_for_file : chemins d'images relatifs → absolus pour l'affichage."""
    return _map_state_paths(state, lambda p: _to_absolute(p, project_dir))


# --- Lecture / écriture des fichiers de carte --------------------------------------------

def read_map(path):
    """Lit une carte (archive .mindy ou JSON simple). Renvoie (état prêt pour l'affichage,
    dossier de la carte)."""
    if zipfile.is_zipfile(path):
        folder = package_work_dir(path)
        target = os.path.join(folder, ATTACHMENTS_DIRNAME)
        os.makedirs(target, exist_ok=True)
        with zipfile.ZipFile(path) as package:
            data = package.read(MAP_ENTRY)
            for info in package.infolist():
                if info.is_dir() or not info.filename.startswith(ATTACHMENTS_DIRNAME + '/'):
                    continue
                # Dossier à plat : seul le nom du fichier compte (aucun chemin de l'archive
                # ne peut écrire en dehors du dossier de travail)
                name = os.path.basename(info.filename)
                if name:
                    with package.open(info) as src, open(os.path.join(target, name), 'wb') as dst:
                        shutil.copyfileobj(src, dst)
        state = json.loads(data.decode('utf-8'))
    else:
        folder = os.path.dirname(os.path.abspath(path))
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    return state_from_file(state, folder), folder


def write_map(state, path, previous_project_dir=None):
    """Enregistre l'état (chemins absolus, tel que produit par le sérialiseur) dans `path`.
    Un .mindy est écrit sous forme d'archive avec tous les fichiers qu'il utilise.
    Renvoie le dossier de la carte après l'enregistrement."""
    if is_package_path(path):
        folder = package_work_dir(path)
    else:
        folder = os.path.dirname(os.path.abspath(path))
    state = state_for_file(state, folder, previous_project_dir)
    text = json.dumps(state, indent=2, ensure_ascii=False)

    if not is_package_path(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return folder

    used = text + "\n" + unquote(text)
    source = os.path.join(folder, ATTACHMENTS_DIRNAME)
    temp_path = path + ".tmp"
    with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as package:
        package.writestr(MAP_ENTRY, text)
        if os.path.isdir(source):
            for name in sorted(os.listdir(source)):
                file_path = os.path.join(source, name)
                if os.path.isfile(file_path) and name in used:
                    package.write(file_path, f"{ATTACHMENTS_DIRNAME}/{name}")
    os.replace(temp_path, path)  # l'ancienne version reste intacte si l'écriture échoue
    return folder


def _map_file_text(path):
    """Texte de la carte d'un fichier .mindy/.json (archive ou JSON simple), ou ''."""
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as package:
                return package.read(MAP_ENTRY).decode('utf-8')
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except (OSError, KeyError, UnicodeDecodeError, zipfile.BadZipFile):
        return ''


# --- Nettoyage des fichiers orphelins ----------------------------------------------------

def referenced_names(app, folder):
    """Ensemble de textes où chercher si un fichier de `folder` est encore utilisé : les
    cartes ouvertes (état courant + historique annuler/rétablir) et les fichiers de carte
    présents dans le même dossier — plusieurs cartes peuvent partager un même
    .mindmap_attachments, il ne faut pas supprimer les images de l'une en ouvrant l'autre."""
    texts = []
    tabs = getattr(app, 'tabs', None)
    if tabs is not None:
        for i in range(tabs.count()):
            ws = tabs.widget(i)
            if not hasattr(ws, 'scene'):
                continue
            states = [app.serializer.get_state(ws)] if hasattr(app, 'serializer') else []
            states += list(getattr(ws, 'undo_stack', [])) + list(getattr(ws, 'redo_stack', []))
            for st in states:
                try:
                    texts.append(st if isinstance(st, str) else json.dumps(st, ensure_ascii=False))
                except (TypeError, ValueError):
                    pass

    project_dir = os.path.dirname(os.path.abspath(folder))
    try:
        for filename in os.listdir(project_dir):
            if filename.lower().endswith(MAP_EXTENSIONS):
                texts.append(_map_file_text(os.path.join(project_dir, filename)))
    except OSError:
        pass
    text = "\n".join(texts)
    # Qt peut encoder certains caractères (espaces, accents) dans les src des images
    return text + "\n" + unquote(text)


def remove_orphans(app, folder, only_images=False):
    """Supprime les fichiers de `folder` dont le nom n'apparaît plus dans aucune carte
    ouverte ni aucun fichier de carte voisin. Un nom présent dans une chaîne plus longue
    est considéré comme utilisé : en cas de doute, on garde le fichier."""
    if not folder or not os.path.isdir(folder):
        return
    haystack = None
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if not os.path.isfile(file_path):
                continue
            if only_images and not filename.lower().endswith(IMAGE_EXTENSIONS):
                continue
            if haystack is None:
                haystack = referenced_names(app, folder)
            if filename not in haystack:
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"Impossible de supprimer le fichier orphelin {filename} : {e}")
    except OSError as e:
        print(f"Erreur lors du nettoyage de {folder} : {e}")
