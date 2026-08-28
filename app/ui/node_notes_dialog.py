from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton


class NodeNotesDialog(QDialog):
    """Fenêtre de prise de notes détaillées (texte brut) associée à un nœud."""

    def __init__(self, parent, node_label, initial_text):
        super().__init__(parent)
        self.setWindowTitle(f"Notes — {node_label}")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Notes du nœud :</b> {node_label}"))

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setPlainText(initial_text or '')
        self.text_edit.setPlaceholderText("Écrivez ici vos notes détaillées pour ce nœud...")
        layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Annuler", self)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Enregistrer", self)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def get_text(self):
        return self.text_edit.toPlainText()
