from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .docx_engine import convert_document, scan_document
from .i18n import tr
from .models import DetectionMode, FormulaCandidate
from .pandoc_backend import PandocBackend, PandocNotFoundError


DARK_STYLE = """
QWidget { background: #0b1220; color: #dbe7f4; font-family: "Segoe UI", "Vazirmatn", "Tahoma"; font-size: 10pt; }
QMainWindow { background: #07101d; }
QFrame#card { background: #101c2d; border: 1px solid #21344b; border-radius: 14px; }
QFrame#dropzone { background: #0d1a2a; border: 2px dashed #3b82f6; border-radius: 16px; }
QFrame#dropzone[drag="true"] { background: #102b46; border-color: #5eead4; }
QLabel#title { font-size: 23pt; font-weight: 700; color: #f8fbff; }
QLabel#subtitle { color: #8fa6bf; font-size: 10.5pt; }
QLabel#section { color: #f8fbff; font-size: 12pt; font-weight: 650; }
QLabel#badge { background: #132b46; color: #7dd3fc; border-radius: 8px; padding: 4px 9px; }
QPushButton { background: #17263a; border: 1px solid #2c415a; border-radius: 9px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #213753; border-color: #4a6a8e; }
QPushButton#primary { background: #2563eb; border-color: #3b82f6; color: white; }
QPushButton#primary:hover { background: #3478f6; }
QPushButton:disabled { color: #5f7388; background: #101a28; border-color: #1b2939; }
QLineEdit, QComboBox { background: #0c1725; border: 1px solid #29405a; border-radius: 8px; padding: 8px; selection-background-color: #2563eb; }
QComboBox::drop-down { border: 0; width: 24px; }
QTableWidget { background: #0c1725; alternate-background-color: #0f1d2e; border: 1px solid #243850; border-radius: 10px; gridline-color: #1d3045; }
QHeaderView::section { background: #142238; color: #a9bdd1; padding: 8px; border: 0; border-right: 1px solid #263a51; font-weight: 650; }
QProgressBar { background: #0c1725; border: 1px solid #263b52; border-radius: 7px; text-align: center; min-height: 14px; }
QProgressBar::chunk { background: #2dd4bf; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QSplitter::handle { background: #1d3045; width: 1px; }
"""

LIGHT_STYLE = """
QWidget { background: #f4f7fb; color: #172033; font-family: "Segoe UI", "Vazirmatn", "Tahoma"; font-size: 10pt; }
QMainWindow { background: #edf2f8; }
QFrame#card { background: #ffffff; border: 1px solid #d6e0eb; border-radius: 14px; }
QFrame#dropzone { background: #f8fbff; border: 2px dashed #3b82f6; border-radius: 16px; }
QFrame#dropzone[drag="true"] { background: #e6f3ff; border-color: #0f766e; }
QLabel#title { font-size: 23pt; font-weight: 700; color: #10213a; }
QLabel#subtitle { color: #5d7188; font-size: 10.5pt; }
QLabel#section { color: #10213a; font-size: 12pt; font-weight: 650; }
QLabel#badge { background: #e1efff; color: #135f9c; border-radius: 8px; padding: 4px 9px; }
QPushButton { background: #ffffff; border: 1px solid #c9d6e4; border-radius: 9px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #eaf2fb; border-color: #7e9bb8; }
QPushButton#primary { background: #2563eb; border-color: #1d4ed8; color: white; }
QPushButton#primary:hover { background: #3478f6; }
QPushButton:disabled { color: #9aa9b8; background: #eef2f6; border-color: #dce4ec; }
QLineEdit, QComboBox { background: #ffffff; border: 1px solid #c9d6e4; border-radius: 8px; padding: 8px; selection-background-color: #2563eb; }
QComboBox::drop-down { border: 0; width: 24px; }
QTableWidget { background: #ffffff; alternate-background-color: #f6f9fc; border: 1px solid #d5dfea; border-radius: 10px; gridline-color: #e2e8f0; }
QHeaderView::section { background: #eaf1f8; color: #41566d; padding: 8px; border: 0; border-right: 1px solid #d2dde8; font-weight: 650; }
QProgressBar { background: #e5edf5; border: 1px solid #c9d6e4; border-radius: 7px; text-align: center; min-height: 14px; }
QProgressBar::chunk { background: #0f9f8f; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QSplitter::handle { background: #d5dfea; width: 1px; }
"""


@dataclass
class QueueItem:
    path: Path
    candidates: list[FormulaCandidate] = field(default_factory=list)
    enabled_ids: set[str] | None = None
    overrides: dict[str, str] = field(default_factory=dict)
    status_key: str = "state_ready"
    output: Path | None = None
    pdf_output: Path | None = None


class WorkerSignals(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)


class TaskWorker(QRunnable):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.function(
                *self.args,
                progress=lambda value, text: self.signals.progress.emit(value, text),
                **self.kwargs,
            )
            self.signals.completed.emit(result)
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.signals.failed.emit(details)


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, translate):
        super().__init__()
        self.setObjectName("dropzone")
        self.setProperty("drag", False)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        icon = QLabel("∑")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 32pt; color: #14b8a6; font-family: Cambria Math;")
        title = QLabel(translate("drop_title"))
        title.setObjectName("section")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(translate("drop_hint"))
        hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(hint)

    def _toggle(self, active: bool) -> None:
        self.setProperty("drag", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._toggle(True)

    def dragLeaveEvent(self, event) -> None:
        self._toggle(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._toggle(False)
        self.files_dropped.emit(
            [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        )
        event.acceptProposedAction()


class PreviewDialog(QDialog):
    def __init__(self, item: QueueItem, language: str, parent=None):
        super().__init__(parent)
        self.item = item
        self.language = language
        self.t = lambda key, **values: tr(language, key, **values)
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if language == "fa" else Qt.LayoutDirection.LeftToRight
        )
        self.setWindowTitle(self.t("review_title", name=item.path.name))
        self.resize(1060, 640)
        layout = QVBoxLayout(self)
        title = QLabel(self.t("review_count", count=len(item.candidates)))
        title.setObjectName("section")
        hint = QLabel(self.t("review_hint"))
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)
        self.table = QTableWidget(len(item.candidates), 6)
        self.table.setHorizontalHeaderLabels(
            [
                self.t("use"),
                self.t("location"),
                self.t("type"),
                self.t("confidence"),
                self.t("detected_source"),
                self.t("normalized"),
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for row, candidate in enumerate(item.candidates):
            use = QTableWidgetItem()
            use.setFlags(use.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            enabled = item.enabled_ids is None or candidate.candidate_id in item.enabled_ids
            use.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            use.setData(Qt.ItemDataRole.UserRole, candidate.candidate_id)
            location = QTableWidgetItem(f"{candidate.paragraph_index + 1}")
            kind = QTableWidgetItem(candidate.kind.value)
            confidence = QTableWidgetItem(f"{candidate.confidence:.0%}")
            source = QTableWidgetItem(candidate.source.replace("\n", " "))
            normalized = QTableWidgetItem(item.overrides.get(candidate.candidate_id, candidate.normalized))
            source.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            normalized.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            for cell in (location, kind, confidence, source):
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            for column, cell in enumerate((use, location, kind, confidence, source, normalized)):
                self.table.setItem(row, column, cell)
            if candidate.repairs:
                source.setToolTip(self.t("repairs_tip", repairs="; ".join(candidate.repairs)))
                source.setForeground(QColor("#d97706"))
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(self.t("save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self.t("cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        enabled: set[str] = set()
        overrides: dict[str, str] = {}
        by_id = {candidate.candidate_id: candidate for candidate in self.item.candidates}
        for row in range(self.table.rowCount()):
            use = self.table.item(row, 0)
            candidate_id = use.data(Qt.ItemDataRole.UserRole)
            if use.checkState() == Qt.CheckState.Checked:
                enabled.add(candidate_id)
            value = self.table.item(row, 5).text().strip()
            if value and value != by_id[candidate_id].normalized:
                overrides[candidate_id] = value
        self.item.enabled_ids = enabled
        self.item.overrides = overrides
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MathFixer", "MathFixer")
        self.language = str(self.settings.value("language", "fa"))
        if self.language not in {"fa", "en"}:
            self.language = "en"
        self.theme_name = str(self.settings.value("theme", "dark"))
        if self.theme_name not in {"dark", "light"}:
            self.theme_name = "dark"
        self.items: list[QueueItem] = []
        self.pool = QThreadPool.globalInstance()
        self._busy = False
        self.resize(1280, 820)
        self.setMinimumSize(1020, 680)
        self._apply_theme()
        self._build_ui()

    def t(self, key: str, **values: object) -> str:
        return tr(self.language, key, **values)

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app:
            app.setStyleSheet(LIGHT_STYLE if self.theme_name == "light" else DARK_STYLE)

    def _capture_settings(self) -> None:
        if hasattr(self, "mode"):
            self.settings.setValue("mode", self.mode.currentData())
            self.settings.setValue("suffix", self.suffix.text())
            self.settings.setValue("reports", self.reports.isChecked())
            self.settings.setValue("atomic", self.atomic.isChecked())
            self.settings.setValue("pdf", self.pdf_checkbox.isChecked())
            self.settings.setValue("overwrite", self.overwrite_checkbox.isChecked())
            self.settings.setValue("output_dir", self.output_dir.text())

    def _build_ui(self) -> None:
        self.setWindowTitle(f"MathFixer {__version__}")
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if self.language == "fa" else Qt.LayoutDirection.LeftToRight
        )
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        title = QLabel("MathFixer")
        title.setObjectName("title")
        subtitle = QLabel(self.t("app_subtitle"))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading, 1)

        help_button = QPushButton(self.t("help"))
        help_button.clicked.connect(self.show_help)
        header.addWidget(help_button)
        self.language_combo = QComboBox()
        self.language_combo.addItem("فارسی", "fa")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(0 if self.language == "fa" else 1)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        header.addWidget(self.language_combo)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.t("theme_dark"), "dark")
        self.theme_combo.addItem(self.t("theme_light"), "light")
        self.theme_combo.setCurrentIndex(0 if self.theme_name == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self._theme_changed)
        header.addWidget(self.theme_combo)
        self.backend_badge = QLabel(self.t("pandoc_checking"))
        self.backend_badge.setObjectName("badge")
        header.addWidget(self.backend_badge)
        root.addLayout(header)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 12, 0)
        left_layout.setSpacing(12)
        self.dropzone = DropZone(self.t)
        self.dropzone.files_dropped.connect(self.add_paths)
        left_layout.addWidget(self.dropzone)

        actions = QHBoxLayout()
        for label, handler in (
            ("add_files", self.choose_files),
            ("add_folder", self.choose_folder),
            ("review_selected", self.preview_selected),
            ("remove_selected", self.remove_selected),
        ):
            button = QPushButton(self.t(label))
            button.clicked.connect(handler)
            actions.addWidget(button)
        actions.addStretch()
        left_layout.addLayout(actions)

        self.queue = QTableWidget(0, 5)
        self.queue.setHorizontalHeaderLabels(
            [self.t("document"), self.t("formulas"), self.t("repairs"), self.t("status"), self.t("output")]
        )
        self.queue.setAlternatingRowColors(True)
        self.queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue.verticalHeader().setVisible(False)
        self.queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.queue.doubleClicked.connect(lambda _: self.preview_selected())
        left_layout.addWidget(self.queue, 1)

        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(330)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(11)
        section = QLabel(self.t("conversion_profile"))
        section.setObjectName("section")
        side_layout.addWidget(section)
        side_layout.addWidget(QLabel(self.t("detection_mode")))
        self.mode = QComboBox()
        self.mode.addItem(self.t("mode_balanced"), DetectionMode.BALANCED.value)
        self.mode.addItem(self.t("mode_safe"), DetectionMode.SAFE.value)
        self.mode.addItem(self.t("mode_aggressive"), DetectionMode.AGGRESSIVE.value)
        saved_mode = str(self.settings.value("mode", DetectionMode.BALANCED.value))
        self.mode.setCurrentIndex(max(0, self.mode.findData(saved_mode)))
        side_layout.addWidget(self.mode)
        mode_note = QLabel(self.t("mode_note"))
        mode_note.setWordWrap(True)
        mode_note.setObjectName("subtitle")
        side_layout.addWidget(mode_note)

        side_layout.addWidget(QLabel(self.t("output_suffix")))
        self.suffix = QLineEdit(str(self.settings.value("suffix", "_mathfixed")))
        self.suffix.setPlaceholderText("_mathfixed")
        side_layout.addWidget(self.suffix)
        self.reports = QCheckBox(self.t("save_reports"))
        self.reports.setChecked(self.settings.value("reports", True, type=bool))
        self.atomic = QCheckBox(self.t("atomic_mode"))
        self.atomic.setChecked(self.settings.value("atomic", True, type=bool))
        self.pdf_checkbox = QCheckBox(self.t("export_pdf"))
        self.pdf_checkbox.setChecked(self.settings.value("pdf", False, type=bool))
        self.overwrite_checkbox = QCheckBox(self.t("replace_outputs"))
        self.overwrite_checkbox.setChecked(self.settings.value("overwrite", False, type=bool))
        side_layout.addWidget(self.reports)
        side_layout.addWidget(self.atomic)
        side_layout.addWidget(self.pdf_checkbox)
        pdf_note = QLabel(self.t("pdf_note"))
        pdf_note.setWordWrap(True)
        pdf_note.setObjectName("subtitle")
        side_layout.addWidget(pdf_note)
        side_layout.addWidget(self.overwrite_checkbox)

        side_layout.addWidget(QLabel(self.t("output_folder")))
        self.output_dir = QLineEdit(str(self.settings.value("output_dir", "")))
        self.output_dir.setPlaceholderText(self.t("same_folder"))
        browse_output = QPushButton(self.t("choose_folder"))
        browse_output.clicked.connect(self.choose_output_folder)
        side_layout.addWidget(self.output_dir)
        side_layout.addWidget(browse_output)
        side_layout.addStretch()
        self.scan_button = QPushButton(self.t("scan_review"))
        self.scan_button.clicked.connect(self.scan_all)
        self.convert_button = QPushButton(self.t("convert_all"))
        self.convert_button.setObjectName("primary")
        self.convert_button.clicked.connect(self.convert_all)
        side_layout.addWidget(self.scan_button)
        side_layout.addWidget(self.convert_button)

        splitter.addWidget(left)
        splitter.addWidget(side)
        splitter.setStretchFactor(0, 1)
        root.addWidget(splitter, 1)

        footer = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label = QLabel(self.t("ready"))
        self.status_label.setObjectName("subtitle")
        footer.addWidget(self.progress, 1)
        footer.addWidget(self.status_label, 2)
        root.addLayout(footer)
        self.setCentralWidget(central)
        self._check_backend()
        self.refresh_queue()

    def _language_changed(self, _index: int = -1) -> None:
        new_language = str(self.language_combo.currentData())
        if new_language == self.language:
            return
        self._capture_settings()
        self.language = new_language
        self.settings.setValue("language", new_language)
        self._build_ui()

    def _theme_changed(self, _index: int = -1) -> None:
        new_theme = str(self.theme_combo.currentData())
        if new_theme == self.theme_name:
            return
        self.theme_name = new_theme
        self.settings.setValue("theme", new_theme)
        self._apply_theme()

    def _check_backend(self) -> None:
        try:
            backend = PandocBackend()
            self.backend_badge.setText("● " + backend.version)
            self.backend_badge.setStyleSheet("color: #0f9f8f;")
        except PandocNotFoundError:
            self.backend_badge.setText("● " + self.t("pandoc_missing"))
            self.backend_badge.setStyleSheet("color: #dc2626;")

    def show_help(self) -> None:
        QMessageBox.information(self, self.t("quick_help_title"), self.t("quick_help_text"))

    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.t("choose_documents"), "", "Word documents (*.docx *.docm)"
        )
        self.add_paths(paths)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("choose_input_folder"))
        if folder:
            self.add_paths(
                [str(path) for path in Path(folder).iterdir() if path.suffix.lower() in {".docx", ".docm"}]
            )

    def choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("choose_output_folder"))
        if folder:
            self.output_dir.setText(folder)

    def add_paths(self, paths: list[str]) -> None:
        existing = {item.path for item in self.items}
        for raw in paths:
            path = Path(raw).expanduser().resolve()
            if path.is_dir():
                self.add_paths(
                    [str(item) for item in path.iterdir() if item.suffix.lower() in {".docx", ".docm"}]
                )
            elif path.suffix.lower() in {".docx", ".docm"} and path not in existing:
                self.items.append(QueueItem(path=path))
                existing.add(path)
        self.refresh_queue()

    def remove_selected(self) -> None:
        for row in sorted({index.row() for index in self.queue.selectedIndexes()}, reverse=True):
            self.items.pop(row)
        self.refresh_queue()

    def refresh_queue(self) -> None:
        self.queue.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            selected = len(item.enabled_ids) if item.enabled_ids is not None else len(item.candidates)
            outputs = []
            if item.output:
                outputs.append(item.output.name)
            if item.pdf_output:
                outputs.append(item.pdf_output.name)
            values = [
                item.path.name,
                str(selected) if item.candidates else "-",
                str(sum(bool(candidate.repairs) for candidate in item.candidates)) if item.candidates else "-",
                self.t(item.status_key),
                " + ".join(outputs) if outputs else "-",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setToolTip(str(item.path))
                self.queue.setItem(row, column, cell)
        enabled = bool(self.items) and not self._busy
        self.scan_button.setEnabled(enabled)
        self.convert_button.setEnabled(enabled)

    def preview_selected(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()})
        if not rows:
            return
        item = self.items[rows[0]]
        if not item.candidates:
            QMessageBox.information(self, self.t("scan_first"), self.t("scan_first_message"))
            return
        if PreviewDialog(item, self.language, self).exec():
            item.status_key = "state_reviewed"
            self.refresh_queue()

    @property
    def selected_mode(self) -> DetectionMode:
        return DetectionMode(str(self.mode.currentData()))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.refresh_queue()

    def _start(self, function, on_done, *args, **kwargs) -> None:
        self._set_busy(True)
        worker = TaskWorker(function, *args, **kwargs)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.completed.connect(on_done)
        worker.signals.failed.connect(self._on_error)
        self.pool.start(worker)

    def _on_progress(self, value: int, _technical_text: str) -> None:
        self.progress.setValue(value)
        self.status_label.setText(self.t("processing", value=value))

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText(self.t("operation_stopped"))
        QMessageBox.critical(self, "MathFixer", message)

    def scan_all(self) -> None:
        if self.items:
            self._capture_settings()
            self._scan_next(0)

    def _scan_next(self, index: int) -> None:
        if index >= len(self.items):
            self._set_busy(False)
            total = sum(len(item.candidates) for item in self.items)
            repairs = sum(sum(bool(candidate.repairs) for candidate in item.candidates) for item in self.items)
            self.progress.setValue(100)
            self.status_label.setText(self.t("scan_complete", total=total, repairs=repairs))
            self.refresh_queue()
            return
        item = self.items[index]
        item.status_key = "state_scanning"
        self.refresh_queue()
        self._start(
            scan_document,
            lambda result, i=index: self._scan_completed(i, result),
            item.path,
            mode=self.selected_mode,
        )

    def _scan_completed(self, index: int, result) -> None:
        item = self.items[index]
        item.candidates = result.report.candidates
        item.enabled_ids = {candidate.candidate_id for candidate in item.candidates}
        item.status_key = "state_scanned"
        self._set_busy(False)
        self.refresh_queue()
        self._scan_next(index + 1)

    def convert_all(self) -> None:
        if self.items:
            self._capture_settings()
            self._convert_next(0)

    def _convert_next(self, index: int) -> None:
        if index >= len(self.items):
            self._set_busy(False)
            self.progress.setValue(100)
            completed = sum(item.status_key == "state_completed" for item in self.items)
            self.status_label.setText(self.t("finished", count=completed))
            self.refresh_queue()
            message = self.t("all_valid_pdf") if self.pdf_checkbox.isChecked() else self.t("all_valid")
            QMessageBox.information(self, "MathFixer", message)
            return
        item = self.items[index]
        destination = (
            Path(self.output_dir.text()).expanduser()
            if self.output_dir.text().strip()
            else item.path.parent
        )
        suffix = self.suffix.text().strip() or "_mathfixed"
        output = destination / f"{item.path.stem}{suffix}{item.path.suffix.lower()}"
        report_path = output.with_suffix(".report.json") if self.reports.isChecked() else None
        pdf_path = output.with_suffix(".pdf") if self.pdf_checkbox.isChecked() else None
        item.status_key = "state_converting"
        self.refresh_queue()
        self._start(
            convert_document,
            lambda result, i=index, path=output: self._convert_completed(i, path, result),
            item.path,
            output,
            mode=self.selected_mode,
            enabled_candidate_ids=item.enabled_ids,
            formula_overrides=item.overrides,
            overwrite=self.overwrite_checkbox.isChecked(),
            fail_on_formula_error=self.atomic.isChecked(),
            create_pdf=self.pdf_checkbox.isChecked(),
            pdf_output_path=pdf_path,
            pdf_engine="auto",
            report_path=report_path,
        )

    def _convert_completed(self, index: int, output: Path, report) -> None:
        item = self.items[index]
        item.candidates = report.candidates
        item.status_key = "state_completed"
        item.output = output
        item.pdf_output = Path(report.pdf_path) if report.pdf_path else None
        self._set_busy(False)
        self.refresh_queue()
        self._convert_next(index + 1)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MathFixer")
    app.setOrganizationName("MathFixer")
    app.setStyle("Fusion")
    font = QFont("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    icon_path = Path(__file__).parent / "resources" / "mathfixer-logo.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
