"""Local persistence tests."""

from pathlib import Path

import pytest

from pipecat_voice_studio.storage import StudioStore


@pytest.fixture
def store(tmp_path: Path) -> StudioStore:
    database = StudioStore(tmp_path / "studio.db")
    database.initialize()
    return database


def test_initialize_seeds_three_active_graphs(store: StudioStore) -> None:
    graphs = store.list_graphs()

    assert {graph["mode"] for graph in graphs} == {"realtime", "cascade", "eval"}
    assert all(graph["active"] for graph in graphs)


def test_semantic_events_are_ordered_and_raw_audio_is_rejected(store: StudioStore) -> None:
    pipeline_id = store.list_graphs()[0]["id"]
    graph = store.get_graph(pipeline_id)
    session_id = store.create_session(pipeline_id, graph, {"llm": "configured-server-side"})

    store.append_event(session_id, "turn.final", {"role": "user", "text": "Hello"})

    assert [event["sequence"] for event in store.list_events(session_id)] == [1, 2]
    with pytest.raises(ValueError, match="Raw audio"):
        store.append_event(session_id, "audio.raw", {"bytes": "forbidden"})


def test_delete_session_cascades_events(store: StudioStore) -> None:
    pipeline_id = store.list_graphs()[0]["id"]
    graph = store.get_graph(pipeline_id)
    session_id = store.create_session(pipeline_id, graph, {})

    store.delete_session(session_id)

    assert store.list_events(session_id) == []


def test_evaluation_results_are_persisted(store: StudioStore) -> None:
    pipeline_id = store.list_graphs()[0]["id"]

    run_id = store.create_eval_run(pipeline_id, "happy-path")
    store.finish_eval_run(run_id, status="passed", result={"passed": True})

    run = store.list_eval_runs(limit=1)[0]
    assert run["id"] == run_id
    assert run["result"] == {"passed": True}
    with pytest.raises(KeyError):
        store.finish_eval_run("missing", status="failed", result={})
