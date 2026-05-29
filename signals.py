# signals.py
from PyQt6.QtCore import QObject, pyqtSignal

class GraphicsSignals(QObject):
    itemDoubleClicked = pyqtSignal(object)
    selectionChanged = pyqtSignal()
    positionChanged = pyqtSignal()