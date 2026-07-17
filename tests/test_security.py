import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from mathfixer.core.security import UnsafePackageError, parse_xml, validate_ooxml_archive


class SecurityTests(unittest.TestCase):
    def test_external_entity_is_not_resolved(self):
        payload = b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]><x>&secret;</x>'
        root = parse_xml(payload)
        self.assertIsNone(root.text)

    def test_duplicate_zip_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "duplicate.docx")
            with ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("word/document.xml", "<document/>")
                archive.writestr("word/document.xml", "<document/>")
            with self.assertRaisesRegex(UnsafePackageError, "duplicate"):
                validate_ooxml_archive(path)


if __name__ == "__main__":
    unittest.main()
