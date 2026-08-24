"""Streamlit application smoke tests."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_command_center_loads() -> None:
    app_path = (
        Path(__file__).parents[1] / "src" / "pipecat_voice_studio" / "ui" / "streamlit_app.py"
    )

    app = AppTest.from_file(app_path).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Command center"
    assert any("CUDA ready" in success.value for success in app.success)
