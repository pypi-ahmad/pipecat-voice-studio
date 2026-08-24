"""Streamlit application smoke tests."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


def test_command_center_loads() -> None:
    app_path = (
        Path(__file__).parents[1] / "src" / "pipecat_voice_studio" / "ui" / "streamlit_app.py"
    )

    app = AppTest.from_file(app_path).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Command center"
    hardware_messages = [message.value for message in [*app.success, *app.info]]
    assert any("ready" in message for message in hardware_messages)


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


@pytest.mark.parametrize("page_name", ["live_session.py", "evaluations.py"])
def test_phase_three_pages_load(page_name: str) -> None:
    page_path = (
        Path(__file__).parents[1]
        / "src"
        / "pipecat_voice_studio"
        / "ui"
        / "app_pages"
        / page_name
    )

    page = AppTest.from_file(page_path).run(timeout=30)

    assert not page.exception
