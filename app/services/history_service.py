import copy

class HistoryService:
    def __init__(self, app):
        self.app = app

    def save_state(self, workspace, current_state_dict: dict):
        """Enregistre une copie profonde de l'état actuel dans la pile d'annulation."""
        if not workspace or getattr(workspace, 'is_applying_state', False):
            return

        if not isinstance(current_state_dict, dict):
            print("[HistoryService] Erreur : l'état fourni n'est pas un dictionnaire.")
            return

        # 🚨 FIX CRITIQUE : Copie profonde pour figer les données à cet instant T
        # Cela évite que les modifications futures des nœuds n'altèrent l'historique
        state_copy = copy.deepcopy(current_state_dict)

        # On évite d'empiler deux fois de suite exactement le même état
        if workspace.undo_stack and workspace.undo_stack[-1] == state_copy:
            return

        workspace.undo_stack.append(state_copy)
        workspace.redo_stack.clear()  # Nouvelle action -> on efface le redo
        workspace.is_dirty = True

    def undo(self, workspace) -> dict:
        """
        Dépile le dernier état de undo, le place dans redo, 
        et retourne l'état précédent à appliquer (ou None).
        """
        if not workspace or len(workspace.undo_stack) < 2:
            return None  # Pas assez d'historique pour annuler

        current_state = workspace.undo_stack.pop()
        workspace.redo_stack.append(current_state)

        # On récupère l'état juste avant, sans le supprimer de la pile de undo
        previous_state = workspace.undo_stack[-1]
        workspace.is_dirty = True
        
        # On renvoie une copie pour que l'application puisse la manipuler sereinement
        return copy.deepcopy(previous_state)

    def redo(self, workspace) -> dict:
        """
        Dépile le dernier état de redo, le remet dans undo,
        et retourne l'état à appliquer (ou None).
        """
        if not workspace or not workspace.redo_stack:
            return None

        next_state = workspace.redo_stack.pop()
        workspace.undo_stack.append(next_state)
        workspace.is_dirty = True
        
        # On renvoie une copie profonde pour protéger la pile
        return copy.deepcopy(next_state)