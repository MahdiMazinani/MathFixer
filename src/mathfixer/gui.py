from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QIcon
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
from .features.ai_assistant import AIAnalysisError, analyze_latex_with_openai
from .features.latex_project import LatexFinding, LatexReport, analyze_latex, repair_latex
from .features.word_to_latex import export_word_to_latex
from .i18n import tr
from .models import DetectionMode, FormulaCandidate, FormulaKind
from .pandoc_backend import PandocBackend, PandocNotFoundError
from .plugins import THESIS_PROFILES

DARK_STYLE = """
QWidget { background: #0b1220; color: #dbe7f4; font-family: "Segoe UI", "Vazirmatn", "Tahoma"; font-size: 10pt; }
QMainWindow { background: #07101d; }
QFrame#card { background: #101c2d; border: 1px solid #21344b; border-radius: 14px; }
QFrame#metric { background: #101c2d; border: 1px solid #21344b; border-radius: 12px; }
QLabel#metricValue { color: #5eead4; font-size: 20pt; font-weight: 750; }
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
QFrame#metric { background: #ffffff; border: 1px solid #d6e0eb; border-radius: 12px; }
QLabel#metricValue { color: #1559c1; font-size: 20pt; font-weight: 750; }
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
    html_report: Path | None = None
    latex_output: Path | None = None
    findings: list[LatexFinding] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class UniversalScanResult:
    report: object


def scan_any_document(
    path: Path,
    *,
    mode: DetectionMode,
    ai_enabled: bool = False,
    thesis_profile: str = "generic",
    progress=None,
) -> UniversalScanResult:
    if path.suffix.lower() != ".tex":
        return scan_document(path, mode=mode, progress=progress)
    if progress:
        progress(20, "Analyzing LaTeX source")
    report = analyze_latex(path, thesis_profile=thesis_profile)
    if ai_enabled:
        try:
            for item in analyze_latex_with_openai(path.read_text(encoding="utf-8", errors="replace")):
                report.findings.append(
                    LatexFinding(
                        "AI_SUGGESTION", item.explanation or item.title, item.suggestion,
                        line=item.line, severity=item.severity,
                    )
                )
        except AIAnalysisError as exc:
            report.findings.append(LatexFinding("AI_UNAVAILABLE", str(exc), severity="warning"))
    report.detected = len(report.changes) + len(report.findings)
    if progress:
        progress(100, "LaTeX analysis completed")
    return UniversalScanResult(report)


def convert_latex_task(path: Path, output: Path, *, progress=None, **options):
    if progress:
        progress(15, "Repairing LaTeX source")
    result = repair_latex(path, output, **options)
    if progress:
        progress(100, "LaTeX repair completed")
    return result


def convert_word_task(
    path: Path,
    output: Path,
    *,
    latex_output_path: Path | None = None,
    progress=None,
    **options,
):
    report = convert_document(path, output, progress=progress, **options)
    if latex_output_path is not None:
        export_word_to_latex(output, latex_output_path)
    return report, latex_output_path


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


class LatexPreviewDialog(QDialog):
    def __init__(self, item: QueueItem, language: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr(language, "change_report"))
        self.resize(980, 620)
        layout = QVBoxLayout(self)
        title = QLabel(tr(language, "latex_review_count", count=len(item.candidates) + len(item.findings)))
        title.setObjectName("section")
        layout.addWidget(title)
        table = QTableWidget(len(item.candidates) + len(item.findings), 4)
        table.setHorizontalHeaderLabels(
            [tr(language, "before"), tr(language, "after"), tr(language, "reason"), tr(language, "location")]
        )
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        row = 0
        for candidate in item.candidates:
            values = [candidate.source, candidate.normalized, "; ".join(candidate.repairs), str(candidate.paragraph_index + 1)]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
            row += 1
        for finding in item.findings:
            values = [finding.message, finding.suggestion, finding.code, str(finding.line or "-")]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
            row += 1
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


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
        self.resize(1280, 840)
        self.setMinimumSize(900, 650)
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
            self.settings.setValue("ai", self.ai_checkbox.isChecked())
            self.settings.setValue("export_latex", self.export_latex_checkbox.isChecked())
            self.settings.setValue("thesis_profile", self.thesis_profile.currentData())
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

        metrics = QHBoxLayout()
        self.metric_values: dict[str, QLabel] = {}
        for key, label_key in (("found", "metric_found"), ("fixed", "metric_fixed"), ("warnings", "metric_warnings"), ("outputs", "metric_outputs")):
            card = QFrame()
            card.setObjectName("metric")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            value = QLabel("0")
            value.setObjectName("metricValue")
            label = QLabel(self.t(label_key))
            label.setObjectName("subtitle")
            card_layout.addWidget(value)
            card_layout.addWidget(label)
            metrics.addWidget(card)
            self.metric_values[key] = value
        root.addLayout(metrics)

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
            ("change_report", self.open_selected_report),
            ("open_output", self.open_selected_output),
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
        side.setFixedWidth(350)
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
        self.export_latex_checkbox = QCheckBox(self.t("export_latex"))
        self.export_latex_checkbox.setChecked(self.settings.value("export_latex", False, type=bool))
        self.ai_checkbox = QCheckBox(self.t("ai_analysis"))
        self.ai_checkbox.setChecked(self.settings.value("ai", False, type=bool))
        self.overwrite_checkbox = QCheckBox(self.t("replace_outputs"))
        self.overwrite_checkbox.setChecked(self.settings.value("overwrite", False, type=bool))
        side_layout.addWidget(self.reports)
        side_layout.addWidget(self.atomic)
        side_layout.addWidget(self.pdf_checkbox)
        side_layout.addWidget(self.export_latex_checkbox)
        side_layout.addWidget(self.ai_checkbox)
        pdf_note = QLabel(self.t("pdf_note"))
        pdf_note.setWordWrap(True)
        pdf_note.setObjectName("subtitle")
        side_layout.addWidget(pdf_note)
        side_layout.addWidget(self.overwrite_checkbox)

        side_layout.addWidget(QLabel(self.t("thesis_profile")))
        self.thesis_profile = QComboBox()
        for profile in THESIS_PROFILES:
            self.thesis_profile.addItem(profile.title_fa if self.language == "fa" else profile.title_en, profile.key)
        saved_profile = str(self.settings.value("thesis_profile", "generic"))
        self.thesis_profile.setCurrentIndex(max(0, self.thesis_profile.findData(saved_profile)))
        side_layout.addWidget(self.thesis_profile)

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
        self.convert_button = QPushButton(self.t("start_repair"))
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
            self, self.t("choose_documents"), "", "Scientific documents (*.docx *.docm *.tex)"
        )
        self.add_paths(paths)

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("choose_input_folder"))
        if folder:
            self.add_paths(
                [str(path) for path in Path(folder).iterdir() if path.suffix.lower() in {".docx", ".docm", ".tex"}]
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
                    [str(item) for item in path.iterdir() if item.suffix.lower() in {".docx", ".docm", ".tex"}]
                )
            elif path.suffix.lower() in {".docx", ".docm", ".tex"} and path not in existing:
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
            if item.latex_output:
                outputs.append(item.latex_output.name)
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
                if column == 3 and item.error:
                    cell.setToolTip(item.error)
                self.queue.setItem(row, column, cell)
        enabled = bool(self.items) and not self._busy
        self.scan_button.setEnabled(enabled)
        self.convert_button.setEnabled(enabled)
        if hasattr(self, "metric_values"):
            found = sum(len(item.candidates) + len(item.findings) for item in self.items)
            fixed = sum(
                len(item.candidates) for item in self.items if item.status_key == "state_completed"
            )
            warnings = sum(len(item.findings) for item in self.items)
            outputs = sum(bool(item.output) + bool(item.pdf_output) + bool(item.latex_output) for item in self.items)
            self.metric_values["found"].setText(str(found))
            self.metric_values["fixed"].setText(str(fixed))
            self.metric_values["warnings"].setText(str(warnings))
            self.metric_values["outputs"].setText(str(outputs))

    def preview_selected(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()})
        if not rows:
            return
        item = self.items[rows[0]]
        if not item.candidates and not item.findings:
            QMessageBox.information(self, self.t("scan_first"), self.t("scan_first_message"))
            return
        if item.path.suffix.lower() == ".tex":
            LatexPreviewDialog(item, self.language, self).exec()
            item.status_key = "state_reviewed"
            self.refresh_queue()
            return
        if PreviewDialog(item, self.language, self).exec():
            item.status_key = "state_reviewed"
            self.refresh_queue()

    def open_selected_report(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()})
        if not rows:
            return
        report = self.items[rows[0]].html_report
        if report and report.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(report)))
        else:
            QMessageBox.information(self, self.t("change_report"), self.t("report_not_ready"))

    def open_selected_output(self) -> None:
        rows = sorted({index.row() for index in self.queue.selectedIndexes()})
        if not rows:
            return
        item = self.items[rows[0]]
        output = item.output or item.pdf_output or item.latex_output
        if output and output.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    @property
    def selected_mode(self) -> DetectionMode:
        return DetectionMode(str(self.mode.currentData()))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.refresh_queue()

    def _start(self, function, on_done, *args, on_error=None, **kwargs) -> None:
        self._set_busy(True)
        worker = TaskWorker(function, *args, **kwargs)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.completed.connect(on_done)
        worker.signals.failed.connect(on_error or self._on_error)
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
            total = sum(len(item.candidates) + len(item.findings) for item in self.items)
            repairs = sum(sum(bool(candidate.repairs) for candidate in item.candidates) for item in self.items)
            self.progress.setValue(100)
            self.status_label.setText(self.t("scan_complete", total=total, repairs=repairs))
            self.refresh_queue()
            return
        item = self.items[index]
        item.status_key = "state_scanning"
        self.refresh_queue()
        self._start(
            scan_any_document,
            lambda result, i=index: self._scan_completed(i, result),
            item.path,
            on_error=lambda message, i=index: self._scan_failed(i, message),
            mode=self.selected_mode,
            ai_enabled=self.ai_checkbox.isChecked(),
            thesis_profile=str(self.thesis_profile.currentData()),
        )

    def _scan_completed(self, index: int, result) -> None:
        item = self.items[index]
        report = result.report
        if isinstance(report, LatexReport):
            item.candidates = [
                FormulaCandidate(
                    part=item.path.name,
                    paragraph_index=max(0, change.line - 1),
                    start=0,
                    end=len(change.before),
                    source=change.before,
                    normalized=change.after,
                    kind=FormulaKind.LATEX_BROKEN,
                    display=False,
                    confidence=0.99,
                    repairs=[change.reason],
                    candidate_id=f"tex:{change.line}:{position}",
                )
                for position, change in enumerate(report.changes)
            ]
            item.findings = report.findings
        else:
            item.candidates = report.candidates
            item.findings = []
        item.enabled_ids = {candidate.candidate_id for candidate in item.candidates}
        item.status_key = "state_scanned"
        self._set_busy(False)
        self.refresh_queue()
        self._scan_next(index + 1)

    def _scan_failed(self, index: int, message: str) -> None:
        item = self.items[index]
        item.status_key = "state_failed"
        item.error = message
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
            failed = sum(item.status_key == "state_failed" for item in self.items)
            self.status_label.setText(self.t("finished", count=completed))
            self.refresh_queue()
            if failed:
                message = self.t("finished_with_errors", completed=completed, failed=failed)
            else:
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
        html_report_path = output.with_suffix(".report.html") if self.reports.isChecked() else None
        pdf_path = output.with_suffix(".pdf") if self.pdf_checkbox.isChecked() else None
        latex_path = (
            output.with_suffix(".tex")
            if self.export_latex_checkbox.isChecked() and item.path.suffix.lower() != ".tex"
            else None
        )
        item.status_key = "state_converting"
        self.refresh_queue()
        if item.path.suffix.lower() == ".tex":
            self._start(
                convert_latex_task,
                lambda result, i=index, path=output, html=html_report_path: self._convert_completed(i, path, result, html),
                item.path,
                output,
                on_error=lambda message, i=index: self._convert_failed(i, message),
                overwrite=self.overwrite_checkbox.isChecked(),
                create_pdf=self.pdf_checkbox.isChecked(),
                report_path=report_path,
                html_report_path=html_report_path,
                language=self.language,
                thesis_profile=str(self.thesis_profile.currentData()),
            )
            return
        self._start(
            convert_word_task,
            lambda result, i=index, path=output, html=html_report_path: self._convert_completed(i, path, result, html),
            item.path,
            output,
            on_error=lambda message, i=index: self._convert_failed(i, message),
            latex_output_path=latex_path,
            mode=self.selected_mode,
            enabled_candidate_ids=item.enabled_ids,
            formula_overrides=item.overrides,
            overwrite=self.overwrite_checkbox.isChecked(),
            fail_on_formula_error=self.atomic.isChecked(),
            create_pdf=self.pdf_checkbox.isChecked(),
            pdf_output_path=pdf_path,
            pdf_engine="auto",
            report_path=report_path,
            html_report_path=html_report_path,
            report_language=self.language,
        )

    def _convert_completed(self, index: int, output: Path, result, html_report_path: Path | None) -> None:
        item = self.items[index]
        latex_output = None
        if isinstance(result, tuple):
            report, latex_output = result
        else:
            report = result
        if hasattr(report, "candidates"):
            item.candidates = report.candidates
        item.status_key = "state_completed"
        item.output = output
        item.pdf_output = Path(report.pdf_path) if report.pdf_path else None
        item.html_report = html_report_path if html_report_path and html_report_path.exists() else None
        item.latex_output = latex_output if latex_output and latex_output.exists() else None
        self._set_busy(False)
        self.refresh_queue()
        self._convert_next(index + 1)

    def _convert_failed(self, index: int, message: str) -> None:
        item = self.items[index]
        item.status_key = "state_failed"
        item.error = message
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
