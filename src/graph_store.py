"""SQLite-backed dual-graph store: Asset Graph (permanent) + Exploration Graph (per-task)."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("agentic.db")


class GraphStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            parent_id INTEGER,
            dedup_key TEXT NOT NULL UNIQUE,
            payload_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS explorations (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL,
            node_type TEXT NOT NULL,
            content TEXT NOT NULL,
            parent_node_id INTEGER,
            edge_type TEXT,
            asset_anchor_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            goal TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS archived_explorations (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL,
            snapshot_json TEXT NOT NULL,
            archived_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            detail_json TEXT,
            created_at TEXT NOT NULL
        );
        """)
        self.con.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Asset Graph (permanent) ──────────────────────────────────────────
    def add_asset(self, typ: str, name: str, parent_id: Optional[int], payload: dict) -> int:
        key = f"{typ}:{name}"
        cur = self.con.execute(
            "INSERT OR IGNORE INTO assets(type,name,parent_id,dedup_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
            (typ, name, parent_id, key, json.dumps(payload), self._now()),
        )
        self.con.commit()
        if cur.lastrowid:
            return cur.lastrowid
        row = self.con.execute("SELECT id FROM assets WHERE dedup_key=?", (key,)).fetchone()
        return row["id"]

    def get_asset(self, asset_id: int) -> Optional[dict]:
        row = self.con.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        return dict(row) if row else None

    def query_assets(self, typ: Optional[str] = None) -> list[dict]:
        if typ:
            rows = self.con.execute("SELECT * FROM assets WHERE type=? ORDER BY id", (typ,)).fetchall()
        else:
            rows = self.con.execute("SELECT * FROM assets ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    # ── Exploration Graph (per-task, archival) ───────────────────────────
    def add_exploration(self, task_id: int, node_type: str, content: str,
                        parent_node_id: Optional[int], edge_type: Optional[str],
                        asset_anchor_id: Optional[int]) -> int:
        cur = self.con.execute(
            "INSERT INTO explorations(task_id,node_type,content,parent_node_id,edge_type,asset_anchor_id,created_at) VALUES(?,?,?,?,?,?,?)",
            (task_id, node_type, content, parent_node_id, edge_type, asset_anchor_id, self._now()),
        )
        self.con.commit()
        return cur.lastrowid

    def get_explorations(self, task_id: int) -> list[dict]:
        rows = self.con.execute(
            "SELECT * FROM explorations WHERE task_id=? ORDER BY id", (task_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def archive_task(self, task_id: int):
        rows = self.get_explorations(task_id)
        snap = json.dumps([{"type": r["node_type"], "content": r["content"]} for r in rows])
        self.con.execute(
            "INSERT INTO archived_explorations(task_id,snapshot_json,archived_at) VALUES(?,?,?)",
            (task_id, snap, self._now()),
        )
        self.con.execute("UPDATE tasks SET status='completed', completed_at=? WHERE id=?", (self._now(), task_id))
        self.con.commit()

    # ── Tasks ────────────────────────────────────────────────────────────
    def create_task(self, goal: str) -> int:
        cur = self.con.execute(
            "INSERT INTO tasks(status,goal,created_at) VALUES('running',?,?)",
            (goal, self._now()),
        )
        self.con.commit()
        return cur.lastrowid

    def get_task(self, task_id: int) -> Optional[dict]:
        row = self.con.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None

    # ── Audit ────────────────────────────────────────────────────────────
    def log(self, actor: str, action: str, detail: Any = None):
        self.con.execute(
            "INSERT INTO audit_log(actor,action,detail_json,created_at) VALUES(?,?,?,?)",
            (actor, action, json.dumps(detail) if detail is not None else None, self._now()),
        )
        self.con.commit()
