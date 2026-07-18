import json
import tempfile
import unittest
from pathlib import Path

from mathfixer.plugins import PluginContext, PluginManager, load_template_adapter


class PluginTests(unittest.TestCase):
    def test_data_only_template_adapter_reports_missing_file_and_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "adapter.json"
            manifest.write_text(
                json.dumps(
                    {
                        "name": "Example University",
                        "version": "1.0",
                        "api_version": "2.0",
                        "required_files": ["university.cls"],
                        "required_commands": [r"\universitytitle"],
                    }
                ),
                encoding="utf-8",
            )
            adapter = load_template_adapter(manifest)
            context = PluginContext(root, root / "main.tex", {"main.tex": "text"})
            findings = PluginManager([adapter]).analyze(context)
            self.assertEqual(
                {item.code for item in findings},
                {"TEMPLATE_FILE_MISSING", "TEMPLATE_COMMAND_MISSING"},
            )
            self.assertTrue(all(item.plugin == "Example University" for item in findings))

    def test_adapter_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory, "adapter.json")
            manifest.write_text(
                json.dumps({"name": "Bad", "version": "1", "required_files": ["../bad.cls"]}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_template_adapter(manifest)

    def test_plugin_context_mappings_are_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = PluginContext(root, root / "main.tex", {"main.tex": "text"})
            with self.assertRaises(TypeError):
                context.sources["main.tex"] = "changed"


if __name__ == "__main__":
    unittest.main()
