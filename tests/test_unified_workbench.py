from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class UnifiedWorkbenchTests(unittest.TestCase):
    def test_root_routes_between_execution_and_read_only_replay(self):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
        app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("file_uploader"))
        app.button(key="run_native").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["native_audit"]["payload"]["workflow"]["terminal"], "STOP")

        app.switch_page("StrokeWeaver-2.0/workbench/app.py").run()
        self.assertFalse(app.exception)
        self.assertFalse(app.get("file_uploader"))
        self.assertEqual(app.metric[0].value, "STOP")
        self.assertIn("MCP verification", [item.value for item in app.subheader])
        self.assertFalse(any(button.label == "Run generated workflow" for button in app.button))
        app.radio[0].set_value("stale").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "REFER")
        app.radio[0].set_value("recovery").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "STOP")
        self.assertEqual(app.session_state["native_audit"]["payload"]["workflow"]["terminal"], "STOP")


if __name__ == "__main__":
    unittest.main()
