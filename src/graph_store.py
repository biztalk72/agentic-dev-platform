"""SQLite-backed dual-graph store: Asset Graph (permanent) + Exploration Graph (per-task)."""
import json
import sqlite3
from pathlib import Path
from typing import Any


class GraphStore:
    def __init__(self, db_path: Path = Path("agentic.db")):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY, type TEXT, name TEXT, parent_id INTEGER,
            dedup_key TEXT UNIQUE, payload_json TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS explorations (
            id INTEGER PRIMARY KEY, task_id INTEGER, node_type TEXT, content TEXT,
            parent_node_id INTEGER, edge_type TEXT, asset_anchor_id INTEGER, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, status TEXT, goal TEXT, created_at TEXT, completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS archived_explorations (
            id INTEGER PRIMARY KEY, task_id INTEGER, snapshot_json TEXT, archived_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY, actor TEXT, action TEXT, detail_json TEXT, created_at TEXT
        );
        """)
        self.con.commit()

    def log(self, actor: str, action: str, detail: dict):
        self.con.execute(
            "INSERT INTO audit_log(actor, action, detail_json, created_at) VALUES (?,?,?,datetime('now'))",
            (actor, action, json.dumps(detail)),
        )
        self.con.commit()

    def add_asset(self, typ: str, name: str, parent_id: int | None, payload: dict) -> int:
        key = f"{typ}:{name}"
        cur = self.con.execute(
            "INSERT OR IGNORE INTO assets(type,name,parent_id,dedup_key,payload_json,created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (typ, name, parent_id, key, json.dumps(payload)),
        )
        self.con.commit()
        row = cur.lastrowid or self.con.execute("SELECT id FROM assets WHERE dedup_key=?", (key,)).fetchone()[0]
        return row

    def add_exploration(self, task_id: int, node_type: str, content: str,
                        parent_id: int | None, edge_type: str, anchor: int | None):
        self.con.execute(
            "INSERT INTO explorations(task_id,node_type,content,parent_node_id,edge_type,asset_anchor_id,created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
            (task_id, node_type, content, parent_id, edge_type, anchor),
        )
        self.con.commit()

    def create_task(self, goal: str) -> int:
        cur = self.con.execute(
            "INSERT INTO tasks(status, goal, created_at) VALUES ('running',?,datetime('now'))", (goal,),
        )
        self.con.commit()
        return cur.lastrowid

    def complete_task(self, task_id: int):
        self.con.execute(
            "UPDATE tasks SET status='completed', completed_at=datetime('now') WHERE id=?", (task_id,),
        )
        self.con.commit()

    def archive_exploration(self, task_id: int):
        rows = self.con.execute(
            "SELECT node_type, content FROM explorations WHERE task_id=?", (task_id,),
        ).fetchall()
        snap = json.dumps([{"type": r["node_type"], "content": r["content"]} for r in rows])
        self.con.execute(
            "INSERT INTO archived_explorations(task_id, snapshot_json, archived_at) VALUES (?,?,datetime('now'))",
            (task_id, snap),
        )
        self.con.commit()

    def get_task_graph(self, task_id: int) -> list[dict]:
        rows = self.con.execute(
            "SELECT node_type, content, edge_type, asset_anchor_id FROM explorations WHERE task_id=? ORDER BY id", (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_assets(self) -> list[dict]:
        rows = self.con.execute("SELECT id, type, name, parent_id, payload_json FROM assets ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_tasks(self) -> list[dict]:
        rows = self.con.execute("SELECT id, status, goal, created_at, completed_at FROM tasks ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def dashboard_snapshot(self) -> dict:
        return {"assets": self.get_assets(), "tasks": self.get_tasks()}
