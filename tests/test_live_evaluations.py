"""Explicit, paid end-to-end Pipecat evaluations."""

import json
import os
from pathlib import Path

import pytest

from pipecat_voice_studio.evaluations import run_evaluation, scenario_names
from pipecat_voice_studio.storage import StudioStore

pytestmark = pytest.mark.live_eval


@pytest.mark.skipif(
    os.getenv("PVS_RUN_LIVE_EVALS") != "1" or not os.getenv("OPENAI_API_KEY"),
    reason="live evaluations require explicit enablement and OPENAI_API_KEY",
)
def test_configured_live_scenarios(tmp_path: Path) -> None:
    store = StudioStore(tmp_path / "live-evaluations.db")
    store.initialize()
    pipeline_id = next(graph["id"] for graph in store.list_graphs() if graph["mode"] == "eval")
    selected = scenario_names(os.getenv("PVS_LIVE_EVAL_SCENARIOS", "all"))

    results = [run_evaluation(store, pipeline_id, scenario) for scenario in selected]
    output = os.getenv("PVS_LIVE_EVAL_OUTPUT")
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    failures = [result for result in results if not result["passed"]]
    assert not failures, json.dumps(failures, indent=2)
