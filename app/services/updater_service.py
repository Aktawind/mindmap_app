import os
import sys
import json
import zipfile
import tempfile
import subprocess
import urllib.request

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Configuration du dépôt GitHub
GITHUB_REPO = "Aktawind/mindmap_app"
CURRENT_VERSION = "v1.0.12"


class CheckUpdateThread(QThread):
    """Thread secondaire pour vérifier silencieusement les mises à jour sans bloquer l'UI."""
    update_available = pyqtSignal(str, str)  # tag_name, download_url

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'MindyApp'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
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
        except Exception as e:
            print(f"Erreur vérification mise à jour : {e}")


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


def check_for_updates(parent_widget):
    """Point d'entrée pour démarrer la recherche de mises à jour."""
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
            perform_update(parent_widget, download_url)

    thread.update_available.connect(on_update_found)
    thread.start()
    # Référence conservée pour éviter que le thread ne soit nettoyé par le garbage collector
    parent_widget._update_thread = thread


def perform_update(parent_widget, download_url):
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

                # 2. Script Batch renforcé pour écraser les fichiers système/lecture seule
                bat_path = os.path.join(temp_dir, "update.bat")
                bat_script = f"""@echo off
rem S'assure que le processus d'origine est bien arrêté
taskkill /F /IM "{exe_name}" > nul 2>&1
timeout /t 3 /nobreak > nul

rem Copie forcée en écrasant TOUT (y compris fichiers cachés / lecture seule)
xcopy /E /Y /I /K /R /H "{source_dir}\\*" "{install_dir}\\"

rem Relance la nouvelle version
cd /d "{install_dir}"
start "" "{exe_name}"

rem Nettoyage
rd /s /q "{temp_dir}"
exit
"""
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_script)

                # Lancement du script Batch
                subprocess.Popen(
                    [bat_path], 
                    creationflags=0 if os.name == 'nt' else 0,
                    shell=True
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