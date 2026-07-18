import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mathfixer.models import ConversionWarning, FormulaCandidate, FormulaKind
from mathfixer.pandoc_backend import PandocBackend, _run_bounded


class PandocBackendResolutionTests(unittest.TestCase):
    def test_frozen_bundle_location_precedes_system_path(self):
        binary_name = "pandoc.exe" if os.name == "nt" else "pandoc"
        with tempfile.TemporaryDirectory() as directory:
            bundled = Path(directory, binary_name)
            bundled.write_bytes(b"placeholder")
            previous = getattr(sys, "_MEIPASS", None)
            sys._MEIPASS = directory
            try:
                backend = PandocBackend()
                self.assertEqual(Path(backend.executable), bundled.resolve())
            finally:
                if previous is None:
                    delattr(sys, "_MEIPASS")
                else:
                    sys._MEIPASS = previous

    def test_bounded_runner_stops_a_hung_child(self):
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_bounded(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=0.2,
            )
        self.assertLess(time.monotonic() - started, 3)

    def test_pandoc_timeout_is_not_retried_for_every_batch(self):
        candidate = FormulaCandidate(
            part="word/document.xml",
            paragraph_index=0,
            start=0,
            end=3,
            source="$x$",
            normalized="x",
            kind=FormulaKind.LATEX_INLINE,
            display=False,
            confidence=1,
        )
        candidates = [
            FormulaCandidate(
                part=candidate.part,
                paragraph_index=index,
                start=0,
                end=3,
                source=f"${index}$",
                normalized=str(index),
                kind=candidate.kind,
                display=False,
                confidence=1,
            )
            for index in range(5)
        ]
        backend = PandocBackend(sys.executable, batch_size=1)
        timeout_warning = ConversionWarning("PANDOC_TIMEOUT", "timed out")
        with patch.object(
            backend,
            "_convert_batch",
            return_value=({}, [timeout_warning]),
        ) as convert_batch:
            _converted, warnings = backend.convert_many(candidates)
        convert_batch.assert_called_once()
        self.assertEqual(warnings[0].code, "PANDOC_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
