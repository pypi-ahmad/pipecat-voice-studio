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


def test_agent_studio_loads_component_and_seed_graphs() -> None:
    page_path = (
        Path(__file__).parents[1]
        / "src"
        / "pipecat_voice_studio"
        / "ui"
        / "app_pages"
        / "agent_studio.py"
    )

    page = AppTest.from_file(page_path).run(timeout=30)

    assert not page.exception
    selected = page.selectbox[0].value
    assert isinstance(selected, dict)
    assert selected["mode"] in {"realtime", "cascade", "eval"}
