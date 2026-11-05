"""Optional real Streamlit AppTest. No browser/clinical validation is implied."""
import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec("streamlit") is not None, "Optional Streamlit demo dependency not installed")
class StreamlitSmokeTests(unittest.TestCase):
    def test_generated_interactions_and_safe_failures(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=30)
        app.run()
        self.assertEqual(len(app.exception), 0)
        app.button(key="run_native").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["native_audit"]["payload"]["workflow"]["terminal"], "STOP")
        app.selectbox(key="fixture_choice").set_value("unknown_units").run()
        app.button(key="run_native").click().run()
        self.assertEqual(app.session_state["native_audit"]["payload"]["workflow"]["terminal"], "REFER")
        app.button(key="run_compare").click().run()
        self.assertEqual(len(app.exception), 0)
        comparison = app.session_state["comparison_audit"]
        self.assertEqual([r["metrics"]["expected_utility"]["decimal"] for r in comparison["payload"]["results"]], [7, 6, 7, 7, 7])
        app.button(key="run_guard").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.session_state["input_audit"]["payload"]["report"]["inference_dispatch_allowed"])
        app.selectbox(key="guard_fault").set_value("different_native_grid").run()
        app.button(key="run_guard").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["input_audit"]["payload"]["report"]["terminal"], "REFER")
        self.assertEqual(len(app.get("file_uploader")), 0)


if __name__ == "__main__":
    unittest.main()
