import os
import sys
import json
import ssl
import socket
import zipfile
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Configuration du dépôt GitHub
GITHUB_REPO = "Aktawind/mindmap_app"
CURRENT_VERSION = "v1.10.0"  # Version actuelle de l'application, à mettre à jour lors des releases


class CheckUpdateThread(QThread):
    """Thread secondaire pour vérifier silencieusement les mises à jour sans bloquer l'UI."""
    update_available = pyqtSignal(str, str)  # tag_name, download_url
    check_finished = pyqtSignal(bool, str)  # (mise_a_jour_trouvee, message_erreur_ou_vide_precis)

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                url, headers={'User-Agent': 'MindyApp', 'Accept': 'application/vnd.github+json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get('tag_name', '')

                if latest_version and latest_version != CURRENT_VERSION:
                    assets = data.get('assets', [])
                    download_url = None
                    for asset in assets:
                        if asset['name'].endswith('.exe') or asset['name'].endswith('.zip'):
                            download_url = asset['browser_download_url']
                            break

                    if download_url:
                        self.update_available.emit(latest_version, download_url)
                        self.check_finished.emit(True, "")
                        return

                self.check_finished.emit(False, "")

        except urllib.error.HTTPError as e:
            if e.code == 403:
                msg = ("GitHub a temporairement limité le nombre de vérifications depuis cette "
                       "connexion (quota de requêtes atteint). Réessayez dans quelques minutes.")
            elif e.code == 404:
                msg = "Aucune release trouvée sur le dépôt GitHub du projet."
            else:
                msg = f"Le serveur GitHub a répondu avec une erreur (HTTP {e.code})."
            print(f"Erreur vérification mise à jour (HTTP {e.code}) : {e}")
            self.check_finished.emit(False, msg)

        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(reason):
                msg = ("Échec de la vérification du certificat de sécurité (SSL). Un antivirus, un "
                       "pare-feu ou un proxy d'entreprise intercepte peut-être la connexion.")
            else:
                msg = (f"Connexion à GitHub impossible : {reason}\n\n"
                       "Un pare-feu ou un antivirus bloque peut-être les connexions sortantes de "
                       "Mindy.exe (fréquent tant que l'application n'est pas signée numériquement).")
            print(f"Erreur vérification mise à jour (URLError) : {e}")
            self.check_finished.emit(False, msg)

        except socket.timeout:
            msg = ("La connexion à GitHub a expiré (délai dépassé). Réessayez, ou vérifiez qu'aucun "
                   "pare-feu ne bloque Mindy.exe.")
            print("Erreur vérification mise à jour : délai dépassé")
            self.check_finished.emit(False, msg)

        except Exception as e:
            print(f"Erreur vérification mise à jour ({type(e).__name__}) : {e}")
            self.check_finished.emit(False, f"Erreur inattendue ({type(e).__name__}) : {e}")


class DownloadThread(QThread):
    """Thread dédié au téléchargement du fichier ZIP pour éviter de figer l'interface graphique."""
    finished_signal = pyqtSignal(bool, str)  # (succès, message_erreur)

    def __init__(self, download_url, zip_path):
        super().__init__()
        self.download_url = download_url
        self.zip_path = zip_path

    def run(self):
        try:
            urllib.request.urlretrieve(self.download_url, self.zip_path)
            self.finished_signal.emit(True, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


def check_for_updates(parent_widget, silent=True):
    """Point d'entrée pour démarrer la recherche de mises à jour.

    En mode silencieux (démarrage de l'application), rien ne s'affiche si aucune
    mise à jour n'est trouvée. En mode manuel (menu À propos), une popup confirme
    à l'utilisateur que le logiciel est à jour, ou signale une erreur réseau.
    """
    thread = CheckUpdateThread(parent_widget)

    def on_update_found(version, download_url):
        reply = QMessageBox.question(
            parent_widget,
            "Mise à jour disponible",
            f"Une nouvelle version ({version}) de Mindy est disponible !\n"
            "Voulez-vous la télécharger et l'installer maintenant ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            perform_update(parent_widget, download_url, version)

    def on_check_finished(update_found, error_msg):
        if update_found or silent:
            return
        if error_msg:
            QMessageBox.warning(
                parent_widget, "Vérification impossible",
                f"Impossible de vérifier les mises à jour.\n\n{error_msg}"
            )
        else:
            QMessageBox.information(
                parent_widget, "À jour",
                f"Vous utilisez déjà la dernière version de Mindy ({CURRENT_VERSION})."
            )

    thread.update_available.connect(on_update_found)
    thread.check_finished.connect(on_check_finished)
    thread.start()
    # Référence conservée pour éviter que le thread ne soit nettoyé par le garbage collector
    parent_widget._update_thread = thread


def _clean_environment_for_relaunch(extra_vars=None):
    """Environnement à transmettre au script de relais (et donc à la nouvelle version).

    L'exécutable "onefile" de PyInstaller place dans l'environnement de son processus des
    variables internes (_PYI_APPLICATION_HOME_DIR, _PYI_PARENT_PROCESS_LEVEL, _MEIPASS2...).
    Héritées par la nouvelle version, elles lui font croire qu'elle est un sous-processus de
    l'ancienne : elle cherche alors sa DLL Python dans le dossier temporaire de l'ancienne
    (supprimé entre-temps) -> "Failed to load Python DLL", ou échoue à valider son
    processus parent -> "Security validation failure". On les retire, et on demande
    explicitement au bootloader de repartir d'un environnement propre."""
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith('_PYI_') and not k.upper().startswith('_MEIPASS')}
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    env.update(extra_vars or {})
    return env


def _old_executable_path(current_exe):
    return current_exe + ".old"


def _replace_executable(current_exe, new_exe):
    """Met l'exécutable en cours d'exécution de côté (renommage autorisé par Windows) et
    copie la nouvelle version à sa place ; restaure l'ancienne en cas d'échec."""
    old_exe = _old_executable_path(current_exe)
    if os.path.exists(old_exe):
        # Reste d'une mise à jour précédente : supprimable, puisque plus exécuté
        os.remove(old_exe)
    os.replace(current_exe, old_exe)
    try:
        shutil.copy2(new_exe, current_exe)
    except Exception:
        if os.path.exists(current_exe):
            os.remove(current_exe)
        os.replace(old_exe, current_exe)
        raise


def _launch_detached(exe_path, cwd):
    """Lance la nouvelle version, détachée de ce processus (qui va se terminer).
    DETACHED_PROCESS / CREATE_NEW_PROCESS_GROUP : elle ne meurt pas avec la console ou le
    groupe de processus de l'ancienne. CREATE_BREAKAWAY_FROM_JOB : elle échappe à un
    éventuel Job Object qui tuerait les enfants à la fermeture — certains environnements
    l'interdisent, on retente alors sans. Un échec n'est pas bloquant : la mise à jour est
    déjà en place, rouvrir Mindy suffit."""
    if os.name != 'nt':
        subprocess.Popen([exe_path], cwd=cwd, env=_clean_environment_for_relaunch(), close_fds=True)
        return
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_BREAKAWAY_FROM_JOB = 0x01000000
    base_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    for flags in (base_flags | CREATE_BREAKAWAY_FROM_JOB, base_flags):
        try:
            subprocess.Popen([exe_path], cwd=cwd, creationflags=flags, close_fds=True,
                             env=_clean_environment_for_relaunch())
            return
        except OSError as e:
            print(f"Relance de la nouvelle version impossible (flags {flags:#x}) : {e}")


def cleanup_previous_update():
    """Au démarrage, supprime l'ancien exécutable mis de côté par la dernière mise à jour.
    Il peut être encore verrouillé quelques secondes par l'ancienne instance qui se
    termine : renvoie False dans ce cas, pour que l'appelant réessaie plus tard."""
    if not getattr(sys, 'frozen', False):
        return True
    old_exe = _old_executable_path(os.path.abspath(sys.executable))
    if not os.path.exists(old_exe):
        return True
    try:
        os.remove(old_exe)
        return True
    except OSError:
        return False


def perform_update(parent_widget, download_url, version=None):
    """Gère l'affichage de la fenêtre, le téléchargement, l'extraction et le remplacement
    de l'exécutable, puis relance la nouvelle version."""
    if not getattr(sys, 'frozen', False):
        QMessageBox.information(
            parent_widget, "Mise à jour",
            "La mise à jour automatique ne fonctionne que depuis Mindy.exe "
            "(et non depuis les sources Python)."
        )
        return
    try:
        current_exe = os.path.abspath(sys.executable)
        install_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)
        
        # 1. Création du dossier temporaire de travail
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "update.zip")

        # 2. Fenêtre de notification sur-mesure (non-acquittable, sans bouton)
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle("Mise à jour")
        dialog.setModal(True)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        dialog.setFixedSize(380, 100)

        layout = QVBoxLayout(dialog)
        lbl_title = QLabel("<b>Mise à jour en cours de téléchargement...</b>", dialog)
        lbl_subtitle = QLabel("L'application va se fermer pour appliquer la nouvelle version.", dialog)
        lbl_subtitle.setWordWrap(True)

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)

        # 3. Traitement une fois le téléchargement terminé par le thread
        def on_download_finished(success, error_msg):
            if not success:
                dialog.reject()
                QMessageBox.critical(parent_widget, "Erreur Mise à jour", f"Échec du téléchargement : {error_msg}")
                return

            try:
                # Extraction du ZIP
                extract_dir = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                # 1. On cherche explicitement l'exécutable dans l'archive
                new_exe = None
                for root, dirs, files in os.walk(extract_dir):
                    if exe_name in files:
                        new_exe = os.path.join(root, exe_name)
                        break

                if not new_exe:
                    raise FileNotFoundError(f"Impossible de trouver {exe_name} dans l'archive téléchargée.")

                # 2. Remplacement de l'exécutable par l'application elle-même, sans script de
                # relais : Windows interdit de supprimer ou d'écraser un .exe en cours
                # d'exécution, mais autorise à le RENOMMER. On met donc l'ancienne version de
                # côté (Mindy.exe.old, supprimé au prochain démarrage) et on copie la nouvelle
                # à sa place. La mise à jour est ainsi déjà appliquée avant la fermeture : même
                # si la relance automatique échoue, il suffit de rouvrir Mindy.
                # (L'ancien relais par script Batch restait bloqué sur "tasklist | find",
                # qui ne se termine jamais dans un processus sans console : la copie n'avait
                # jamais lieu.)
                _replace_executable(current_exe, new_exe)

                # Mémorise la version installée pour que la prochaine instance qui démarre
                # affiche un message de confirmation ("Mindy a été mis à jour à la version vX")
                if version and hasattr(parent_widget, 'settings'):
                    parent_widget.settings.setValue("pending_update_version", version)
                    parent_widget.settings.sync()

                # Dernière sauvegarde des cartes déjà enregistrées avant de fermer
                if hasattr(parent_widget, 'autosave_all_tabs'):
                    try:
                        parent_widget.autosave_all_tabs()
                    except Exception as e:
                        print(f"Sauvegarde avant mise à jour impossible : {e}")

                shutil.rmtree(temp_dir, ignore_errors=True)
                _launch_detached(current_exe, install_dir)

                # Termine le processus brutalement pour libérer les DLLs sans délai
                os._exit(0)

            except Exception as e:
                dialog.reject()
                QMessageBox.critical(parent_widget, "Erreur Mise à jour", f"Échec de l'installation : {e}")

        # 4. Lancement du téléchargement en arrière-plan
        download_thread = DownloadThread(download_url, zip_path)
        download_thread.finished_signal.connect(on_download_finished)
        
        # Référence conservée sur l'objet parent
        parent_widget._download_thread = download_thread
        
        download_thread.start()
        
        # Affiche la boite de dialogue de manière bloquante jusqu'au sys.exit(0)
        dialog.exec()

    except Exception as e:
        QMessageBox.critical(parent_widget, "Erreur Mise à jour", f"Échec de l'initialisation : {e}")