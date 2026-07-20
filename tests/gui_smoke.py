import tempfile
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from PySide6.QtCore import QEventLoop, QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from smoke_document import write_smoke_document

from mathfixer.gui import MainWindow, QueueItem, scan_any_document
from mathfixer.models import ConversionReport, ConversionWarning


def run_real_conversion(app: QApplication) -> None:
    """Exercise QThreadPool, signal delivery, Pandoc and DOCX publication together."""
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory, "small-formulas.docx")
        write_smoke_document(source)
        occupied = Path(directory, "small-formulas_mathfixed.docx")
        occupied.write_bytes(b"existing output must not be replaced")
        window = MainWindow()
        window.reports.setChecked(False)
        window.atomic.setChecked(False)
        window.pdf_checkbox.setChecked(False)
        window.export_latex_checkbox.setChecked(False)
        window.ai_provider.setCurrentIndex(window.ai_provider.findData("off"))
        window.thesis_profile.setCurrentIndex(window.thesis_profile.findData("generic"))
        window.add_paths([str(source)])

        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(25)
        poll.timeout.connect(lambda: loop.quit() if not window._busy else None)
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        timed_out: list[bool] = []

        def stop_on_timeout() -> None:
            timed_out.append(True)
            loop.quit()

        watchdog.timeout.connect(stop_on_timeout)
        with (
            patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok),
            patch.object(QMessageBox, "critical", return_value=QMessageBox.StandardButton.Ok),
        ):
            window.process_all()
            self_retained = bool(window._workers)
            poll.start()
            watchdog.start(30_000)
            loop.exec()
        poll.stop()
        watchdog.stop()
        window.pool.waitForDone(5_000)
        app.processEvents()

        assert self_retained, "TaskWorker was not retained after scheduling"
        assert not timed_out, window.items[0].progress_detail or "GUI conversion timed out"
        assert not window._busy
        assert window.items[0].status_key in {"state_completed", "state_completed_warning"}
        assert window.items[0].output is not None
        assert window.items[0].output.exists()
        assert window.items[0].output.name == "small-formulas_mathfixed_2.docx"
        with ZipFile(window.items[0].output) as archive:
            root = etree.fromstring(archive.read("word/document.xml"))
        namespaces = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        }
        assert not root.xpath(
            ".//m:oMathPara[not(ancestor::w:p)] | .//m:oMath[not(ancestor::w:p)]",
            namespaces=namespaces,
        ), "Microsoft Word rejects Office Math containers outside w:p"
        assert occupied.read_bytes() == b"existing output must not be replaced"
        assert window.items[0].progress_value == 100
        assert not window._workers, "finished TaskWorker was not released"
        window.close()


def main() -> None:
    app = QApplication([])
    QSettings("MathFixer", "MathFixer").clear()

    window = MainWindow()
    assert window.ai_provider.currentData() == "off"
    assert window.thesis_profile.currentData() == "generic"
    assert not hasattr(window, "scan_button")

    run_real_conversion(app)

    calls: list[tuple[str, int]] = []
    window.items = [QueueItem(Path("sample.docx"))]
    window._convert_next = lambda index: calls.append(("convert", index))  # type: ignore[method-assign]
    window._scan_next = lambda index: calls.append(("scan", index))  # type: ignore[method-assign]
    window.process_all()
    assert calls == [("convert", 0)]

    recovery = MainWindow()
    recovery.items = [QueueItem(Path("sample.docx"))]
    captured: dict[str, object] = {}

    def capture_start(function, _on_done, *_args, **kwargs):
        captured["function"] = function
        captured["ai_enabled"] = kwargs["ai_enabled"]

    recovery._start = capture_start  # type: ignore[method-assign]
    recovery._convert_failed(0, "Atomic conversion stopped")
    assert recovery.items[0].status_key == "state_preparing_review"
    assert captured == {"function": scan_any_document, "ai_enabled": False}

    completed = MainWindow()
    completed.items = [QueueItem(Path("sample.docx"))]
    completed._convert_next = lambda _index: None  # type: ignore[method-assign]
    report = ConversionReport(
        input_path="sample.docx",
        success=True,
        warnings=[ConversionWarning("PDF_EXPORT_FAILED", "PDF timed out")],
    )
    completed._convert_completed(0, Path("sample_mathfixed.docx"), report, None)
    assert completed.items[0].status_key == "state_completed_warning"
    assert completed.items[0].output == Path("sample_mathfixed.docx")

    print("MathFixer GUI recovery smoke passed")
    window.close()
    recovery.close()
    completed.close()
    app.quit()


if __name__ == "__main__":
    main()
