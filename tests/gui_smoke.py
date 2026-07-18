from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from mathfixer.gui import MainWindow, QueueItem, scan_any_document
from mathfixer.models import ConversionReport, ConversionWarning


def main() -> None:
    app = QApplication([])
    QSettings("MathFixer", "MathFixer").clear()

    window = MainWindow()
    assert window.ai_provider.currentData() == "off"
    assert window.thesis_profile.currentData() == "generic"
    assert not hasattr(window, "scan_button")

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
