"""Emplacement des images d'une carte (images de nœud, images des notes, fond de canevas).

Les images vivent dans un dossier .mindmap_attachments placé à côté du fichier .mindy,
comme les pièces jointes. En mémoire (scène, historique annuler/rétablir), les chemins sont
absolus pour que l'affichage fonctionne tel quel ; dans le fichier enregistré, ils sont
relatifs au dossier de la carte, pour que l'ensemble puisse être déplacé ou copié sur un
autre PC. Une carte jamais enregistrée range ses images dans un dossier de travail de
l'application, puis elles sont recopiées à côté de la carte lors du premier enregistrement.
"""
import copy
import json
import os
import re
import shutil
from datetime import datetime
from urllib.parse import unquote

from PyQt6.QtCore import QStandardPaths

ATTACHMENTS_DIRNAME = ".mindmap_attachments"
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
MAP_EXTENSIONS = ('.mindy', '.json')

_IMG_SRC_RE = re.compile(r'(<img[^>]*\ssrc=")([^"]+)(")', re.IGNORECASE)


def _unsaved_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
    return os.path.join(base or os.path.abspath("."), "Mindy", "cartes_non_enregistrees", ATTACHMENTS_DIRNAME)


def attachments_dir(ws):
    """Dossier où ranger les images du workspace (créé au besoin)."""
    file_path = getattr(ws, 'current_file_path', None) if ws else None
    if file_path:
        target = os.path.join(os.path.dirname(os.path.abspath(file_path)), ATTACHMENTS_DIRNAME)
    else:
        target = _unsaved_dir()
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


def state_for_file(state, map_path, previous_map_path=None):
    """Prépare l'état à écrire dans map_path : chemins d'images relatifs, images recopiées
    à côté de la carte. Les pièces jointes copiées sont aussi recopiées lors d'un
    « Enregistrer sous » vers un autre dossier."""
    project_dir = os.path.dirname(os.path.abspath(map_path))
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

    if previous_map_path:
        old_dir = os.path.dirname(os.path.abspath(previous_map_path))
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


def state_from_file(state, map_path):
    """Inverse de state_for_file : chemins d'images relatifs → absolus pour l'affichage."""
    project_dir = os.path.dirname(os.path.abspath(map_path))
    return _map_state_paths(state, lambda p: _to_absolute(p, project_dir))


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
                try:
                    with open(os.path.join(project_dir, filename), 'r', encoding='utf-8') as f:
                        texts.append(f.read())
                except (OSError, UnicodeDecodeError):
                    pass
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
