import os
import sys
import tempfile
import unittest
from pathlib import Path

from mathfixer.pandoc_backend import PandocBackend


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


if __name__ == "__main__":
    unittest.main()
