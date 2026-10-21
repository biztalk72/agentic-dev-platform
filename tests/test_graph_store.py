# 그래프 저장소(자산 dedup, 탐색 노드, 아카이브, 감사 로그) 단위 테스트
from src.graph_store import GraphStore


def make_store(tmp_path):
    return GraphStore(tmp_path / "test.db")


def test_add_asset_dedups_by_type_and_name(tmp_path):
    store = make_store(tmp_path)
    first = store.add_asset("service", "api", None, {"lang": "python"})
    second = store.add_asset("service", "api", None, {"lang": "other"})
    assert first == second
    assert len(store.query_assets()) == 1


def test_add_asset_distinct_keys_create_rows(tmp_path):
    store = make_store(tmp_path)
    a = store.add_asset("service", "api", None, {})
    b = store.add_asset("doc", "api", None, {})
    assert a != b
    assert len(store.query_assets()) == 2
    assert len(store.query_assets(typ="doc")) == 1


def test_exploration_nodes_scoped_to_task(tmp_path):
    store = make_store(tmp_path)
    t1 = store.create_task("goal one")
    t2 = store.create_task("goal two")
    store.add_exploration(t1, "fact", "fact for t1", None, "yields", None)
    store.add_exploration(t2, "hint", "hint for t2", None, "yields", None)
    assert [r["content"] for r in store.get_explorations(t1)] == ["fact for t1"]
    assert [r["content"] for r in store.get_explorations(t2)] == ["hint for t2"]


def test_archive_task_marks_completed_and_snapshots(tmp_path):
    store = make_store(tmp_path)
    task_id = store.create_task("goal")
    store.add_exploration(task_id, "fact", "something", None, "yields", None)
    assert store.get_task(task_id)["status"] == "running"

    store.archive_task(task_id)

    task = store.get_task(task_id)
    assert task["status"] == "completed"
    assert task["completed_at"] is not None
    archived = store.con.execute(
        "SELECT * FROM archived_explorations WHERE task_id=?", (task_id,)
    ).fetchall()
    assert len(archived) == 1


def test_audit_log_roundtrip(tmp_path):
    store = make_store(tmp_path)
    assert not store.has_log("dashboard", "rendered")
    store.log("dashboard", "rendered", {"path": "x"})
    assert store.has_log("dashboard", "rendered")
