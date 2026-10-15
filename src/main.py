#!/usr/bin/env python3
"""MVP entrypoint: event-driven dual-graph loop with stub workers."""
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

DB = Path("agentic.db")
OUT = Path("output")
OUT.mkdir(exist_ok=True)


def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript("""
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
    con.commit()
    return con


def log(con, actor, action, detail):
    con.execute(
        "INSERT INTO audit_log(actor, action, detail_json, created_at) VALUES (?,?,?,datetime('now'))",
        (actor, action, json.dumps(detail)),
    )
    con.commit()


def add_asset(con, typ, name, parent_id, payload):
    key = f"{typ}:{name}"
    cur = con.execute(
        "INSERT OR IGNORE INTO assets(type,name,parent_id,dedup_key,payload_json,created_at) VALUES (?,?,?,?,?,datetime('now'))",
        (typ, name, parent_id, key, json.dumps(payload)),
    )
    con.commit()
    return cur.lastrowid or con.execute("SELECT id FROM assets WHERE dedup_key=?", (key,)).fetchone()[0]


def add_exploration(con, task_id, node_type, content, parent_id, edge_type, anchor):
    con.execute(
        "INSERT INTO explorations(task_id,node_type,content,parent_node_id,edge_type,asset_anchor_id,created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
        (task_id, node_type, content, parent_id, edge_type, anchor),
    )
    con.commit()


async def hitl_gate(intent):
    print(f"\n[GATE] Intent: {intent}. Approve? [y/N] ", end="", flush=True)
    # MVP: auto-deny on timeout simulation; in demo mode we just log and proceed as approved for non-gated intents.
    return True


async def orchestrator_plan(con, task_id):
    # Stub planner: fixed 3-step chain for the demo.
    return [
        {"step": 1, "worker": "collector", "intent": "ingest sample log + VLM frame summary"},
        {"step": 2, "worker": "prd", "intent": "draft PRD from collected facts"},
        {"step": 3, "worker": "reviewer", "intent": "lineage-check PRD against findings", "gate": False},
    ]


async def worker_run(con, task_id, step):
    if step["worker"] == "collector":
        aid = add_asset(con, "service", "demo-api", None, {"lang": "python"})
        add_exploration(con, task_id, "fact", "sample log: 3 errors on /login", None, "yields", aid)
        add_exploration(con, task_id, "hint", "VLM: submit button disabled on mobile", None, "yields", aid)
        log(con, "collector", "ingested", {"assets": 1, "facts": 1, "hints": 1})
    elif step["worker"] == "prd":
        prd = "# Demo PRD\n\n## Problem\nLogin errors on mobile.\n\n## Requirements\n- Fix disabled submit button on mobile viewport.\n"
        (OUT / "PRD.md").write_text(prd)
        aid = add_asset(con, "doc", "PRD.md", None, {"path": str(OUT / "PRD.md")})
        add_exploration(con, task_id, "finding", "PRD drafted at output/PRD.md", None, "yields", aid)
        log(con, "prd", "wrote", {"path": str(OUT / "PRD.md")})
    elif step["worker"] == "reviewer":
        rows = con.execute("SELECT node_type, content FROM explorations WHERE task_id=?", (task_id,)).fetchall()
        orphans = [c for t, c in rows if t == "finding" and "PRD" not in c]
        add_exploration(con, task_id, "finding", f"lineage-check: {len(orphans)} orphan findings", None, "proves", None)
        log(con, "reviewer", "checked", {"orphans": len(orphans)})
        # archive exploration graph (policy)
        snap = json.dumps([{"type": t, "content": c} for t, c in rows])
        con.execute(
            "INSERT INTO archived_explorations(task_id, snapshot_json, archived_at) VALUES (?,?,datetime('now'))",
            (task_id, snap),
        )
        con.execute("UPDATE tasks SET status='completed', completed_at=datetime('now') WHERE id=?", (task_id,))
        con.commit()
        log(con, "archive-policy", "archived", {"task_id": task_id})


async def demo(con):
    cur = con.execute("INSERT INTO tasks(status, goal, created_at) VALUES ('running','demo goal',datetime('now'))")
    con.commit()
    task_id = cur.lastrowid
    log(con, "orchestrator", "started", {"task_id": task_id})
    for step in await orchestrator_plan(con, task_id):
        if step.get("gate"):
            ok = await hitl_gate(step["intent"])
            if not ok:
                log(con, "hitl", "denied", step)
                continue
        await worker_run(con, task_id, step)
    print("\nDemo complete. Outputs:")
    print(" -", OUT / "PRD.md")
    print(" -", DB)
    for row in con.execute("SELECT type, name FROM assets"):
        print(" - asset:", row)
    for row in con.execute("SELECT task_id, status FROM tasks"):
        print(" - task:", row)
    for row in con.execute("SELECT task_id, length(snapshot_json) FROM archived_explorations"):
        print(" - archived exploration bytes:", row)


async def main():
    con = init_db()
    if "--demo" in sys.argv:
        await demo(con)
    else:
        print("Usage: python3 -m src.main --demo")
        print("SQLite schema initialized at", DB)


if __name__ == "__main__":
    asyncio.run(main())
