# services/history_service.py

class HistoryService:
    @staticmethod
    def save_state(workspace, current_state_str: str):
        """Enregistre l'état actuel dans la pile d'annulation du workspace."""
        if workspace.is_applying_state:
            return

        # On évite d'empiler deux fois de suite exactement le même état
        if workspace.undo_stack and workspace.undo_stack[-1] == current_state_str:
            return

        workspace.undo_stack.append(current_state_str)
        workspace.redo_stack.clear()  # Nouvelle action -> on efface le redo
        workspace.is_dirty = True

    @staticmethod
    def undo(workspace) -> str:
        """
        Dépile le dernier état de undo, le place dans redo, 
        et retourne l'état précédent à appliquer (ou None).
        """
        if len(workspace.undo_stack) < 2:
            return None  # Pas assez d'historique pour annuler (l'état initial doit rester)

        # L'état actuel de la scène est au sommet du undo_stack
        current_state = workspace.undo_stack.pop()
        workspace.redo_stack.append(current_state)

        # L'état précédent devient le nouvel état actif
        previous_state = workspace.undo_stack[-1]
        workspace.is_dirty = True
        return previous_state

    @staticmethod
    def redo(workspace) -> str:
        """
        Dépile le dernier état de redo, le remet dans undo,
        et retourne l'état à appliquer (ou None).
        """
        if not workspace.redo_stack:
            return None

        next_state = workspace.redo_stack.pop()
        workspace.undo_stack.append(next_state)
        workspace.is_dirty = True
        return next_state