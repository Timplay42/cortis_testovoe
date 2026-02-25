import json
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class FormPreviewDialog(QDialog):
    def __init__(self, patient: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предпросмотр формы")
        self.resize(520, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("КАРТА ПАЦИЕНТА")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)

        fio_row = QHBoxLayout()
        fio_label = QLabel("ФИО:")
        fio_value = QLabel(patient.get("fio", ""))
        fio_row.addWidget(fio_label)
        fio_row.addSpacing(36)
        fio_row.addWidget(fio_value)
        fio_row.addStretch()

        birth_row = QHBoxLayout()
        birth_label = QLabel("Дата рождения:")
        birth_value = QLabel(patient.get("birth_date", ""))
        birth_row.addWidget(birth_label)
        birth_row.addSpacing(12)
        birth_row.addWidget(birth_value)
        birth_row.addStretch()

        layout.addWidget(title)
        layout.addLayout(fio_row)
        layout.addLayout(birth_row)
        layout.addStretch()


class PatientsWindow(QMainWindow):
    def __init__(self, data_path: Path):
        super().__init__()
        self.data_path = data_path
        self.patients = []
        self.visible_indices = []

        self.setWindowTitle("Список пациентов")
        self.resize(860, 520)

        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ФИО", "Дата рождения"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().setStretchLastSection(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.table)
        self.setCentralWidget(container)

        self.load_data()
        self.refresh_table()

    def load_data(self):
        if not self.data_path.exists():
            self.patients = []
            return

        with self.data_path.open("r", encoding="utf-8") as f:
            self.patients = json.load(f)

    def save_data(self):
        with self.data_path.open("w", encoding="utf-8") as f:
            json.dump(self.patients, f, ensure_ascii=False, indent=4)

    def refresh_table(self):
        self.table.setRowCount(0)
        self.visible_indices = []

        for idx, patient in enumerate(self.patients):
            if patient.get("deleted", 0) == 1:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(patient.get("fio", "")))
            self.table.setItem(row, 1, QTableWidgetItem(patient.get("birth_date", "")))
            self.visible_indices.append(idx)

        self.table.resizeColumnsToContents()

    def show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if item is None:
            return

        row = item.row()
        menu = QMenu(self)

        build_form_action = menu.addAction("Сформировать выходную форму")
        delete_row_action = menu.addAction("Удалить строку")

        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen == build_form_action:
            self.open_form_preview(row)
        elif chosen == delete_row_action:
            self.delete_patient(row)

    def open_form_preview(self, row: int):
        patient = self.get_patient_by_visible_row(row)
        if patient is None:
            return

        dialog = FormPreviewDialog(patient, self)
        dialog.exec_()

    def delete_patient(self, row: int):
        real_index = self.get_real_index(row)
        if real_index is None:
            return

        patient = self.patients[real_index]
        fio = patient.get("fio", "пациент")

        answer = QMessageBox.question(
            self,
            "Удаление",
            f"Удалить строку для '{fio}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        self.patients[real_index]["deleted"] = 1
        self.save_data()
        self.refresh_table()

    def get_real_index(self, visible_row: int):
        if visible_row < 0 or visible_row >= len(self.visible_indices):
            return None
        return self.visible_indices[visible_row]

    def get_patient_by_visible_row(self, visible_row: int):
        real_index = self.get_real_index(visible_row)
        if real_index is None:
            return None
        return self.patients[real_index]


def main():
    app = QApplication(sys.argv)

    data_path = Path(__file__).resolve().parent.parent / "clientList"
    window = PatientsWindow(data_path)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
