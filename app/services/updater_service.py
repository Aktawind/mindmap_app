import os
import sys
import json
import ssl
import socket
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.error

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Configuration du dépôt GitHub
GITHUB_REPO = "Aktawind/mindmap_app"
CURRENT_VERSION = "v1.9.0"  # Version actuelle de l'application, à mettre à jour lors des releases


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


def perform_update(parent_widget, download_url, version=None):
    """Gère l'affichage de la fenêtre, le téléchargement, l'extraction et le relais au script Batch."""
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

                # 1. On cherche explicitement le répertoire qui CONTIENT l'exécutable
                source_dir = None
                for root, dirs, files in os.walk(extract_dir):
                    if exe_name in files:
                        source_dir = root
                        break

                if not source_dir:
                    raise FileNotFoundError(f"Impossible de trouver {exe_name} dans l'archive téléchargée.")

                # 2. Script Batch de relais. Points importants :
                # - Il tourne SANS console (DETACHED_PROCESS, plus bas) : la commande
                #   "timeout" y échoue immédiatement ("redirection d'entrée non prise en
                #   charge") au lieu d'attendre. Toutes les pauses passent donc par
                #   "ping -n N 127.0.0.1", qui attend ~N-1 secondes sans console.
                # - On attend que l'ancienne version soit réellement fermée, puis on retente
                #   la copie tant que l'exécutable est encore verrouillé (antivirus...),
                #   au lieu de parier sur des délais fixes.
                # - Aucun chemin n'est écrit dans le script : sans console, cmd.exe ne peut
                #   pas passer en UTF-8 (chcp échoue) et lirait mal tout chemin accentué
                #   (ex : nom d'utilisateur Windows). Les chemins lui sont transmis par des
                #   variables d'environnement (Unicode), et le script reste en pur ASCII.
                bat_path = os.path.join(temp_dir, "update.bat")
                bat_script = r"""@echo off

rem Attend la fermeture de l'ancienne version (15 s max), puis force si besoin
set WAIT_TRIES=0
:wait_exit
tasklist /FI "IMAGENAME eq %MINDY_EXE%" | find /I "%MINDY_EXE%" > nul
if errorlevel 1 goto copy_files
set /a WAIT_TRIES+=1
if %WAIT_TRIES% GEQ 15 (
    taskkill /F /IM "%MINDY_EXE%" > nul 2>&1
    ping -n 3 127.0.0.1 > nul
    goto copy_files
)
ping -n 2 127.0.0.1 > nul
goto wait_exit

rem Copie de la nouvelle version, retentee tant que l'exe est verrouille (10 essais)
:copy_files
set COPY_TRIES=0
:copy_retry
set /a COPY_TRIES+=1
xcopy /E /Y /I /K /R /H /Q "%MINDY_SOURCE%\*" "%MINDY_INSTALL%\" < nul > nul 2>&1
if not errorlevel 1 goto launch
if %COPY_TRIES% GEQ 10 goto launch
ping -n 3 127.0.0.1 > nul
goto copy_retry

rem Laisse l'antivirus analyser le nouvel executable avant de le lancer
:launch
ping -n 4 127.0.0.1 > nul
cd /d "%MINDY_INSTALL%"
start "" "%MINDY_EXE%"

rem Nettoyage (apres un delai, pour ne pas supprimer le script en cours de lecture)
ping -n 6 127.0.0.1 > nul
rd /s /q "%MINDY_TEMP%" > nul 2>&1
exit
"""
                with open(bat_path, "w", encoding="ascii") as f:
                    f.write(bat_script)

                # Lancement du script Batch, complètement détaché du processus actuel :
                # - DETACHED_PROCESS / CREATE_NEW_PROCESS_GROUP : évite qu'il soit tué en
                #   cascade si ce processus est rattaché à une console ou un groupe de
                #   processus qui disparaît avec lui.
                # - CREATE_BREAKAWAY_FROM_JOB : l'échappe de tout Job Object (Windows
                #   Terminal, certains lanceurs/EDR) qui tuerait ses enfants à la fermeture
                #   de ce processus — sinon le script (et donc le relais vers la nouvelle
                #   version) peut être interrompu par le os._exit(0) ci-dessous.
                if os.name == 'nt':
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    CREATE_BREAKAWAY_FROM_JOB = 0x01000000
                    creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
                else:
                    creation_flags = 0

                # Mémorise la version installée pour que la prochaine instance qui démarre
                # (relancée par le script Batch ci-dessus, ou manuellement par l'utilisateur
                # si ce relais automatique échoue) affiche un message de confirmation propre
                # ("Mindy a été mis à jour à la version vX") plutôt que rien, ou plutôt que
                # seule l'éventuelle erreur transitoire du bootloader ne soit visible.
                if version and hasattr(parent_widget, 'settings'):
                    parent_widget.settings.setValue("pending_update_version", version)
                    parent_widget.settings.sync()

                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path] if os.name == 'nt' else [bat_path],
                    creationflags=creation_flags,
                    close_fds=True,
                    env=_clean_environment_for_relaunch({
                        "MINDY_EXE": exe_name,
                        "MINDY_SOURCE": source_dir,
                        "MINDY_INSTALL": install_dir,
                        "MINDY_TEMP": temp_dir,
                    }),
                )

                # --- CHANGEMENT CLÉ ICI ---
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