import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt

POLICY_FILE = "policy.json"

def load_policy():
    with open(POLICY_FILE, "r") as f:
        return json.load(f)

def save_policy(data):
    with open(POLICY_FILE, "w") as f:
        json.dump(data, f, indent=4)

class PolicyUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SHL Provider Priority Editor")

        self.policy = load_policy()

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Provider", "Enabled", "Timeout"])

        # Drag & drop reorder
        self.table.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setDefaultDropAction(Qt.DropAction.MoveAction)

        layout.addWidget(self.table)

        self.save_btn = QPushButton("Save Priorities")
        self.save_btn.clicked.connect(self.save_priorities)
        layout.addWidget(self.save_btn)

        self.load_table()

    def load_table(self):
        providers = list(self.policy.keys())
        self.table.setRowCount(len(providers))

        for row, name in enumerate(providers):
            cfg = self.policy[name]
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(cfg["enabled"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(cfg["timeout"])))

    def save_priorities(self):
        # Uusi järjestys taulusta
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            self.policy[name]["priority"] = row + 1

        save_policy(self.policy)
        print("Saved.")

app = QApplication([])
ui = PolicyUI()
ui.show()
app.exec()

