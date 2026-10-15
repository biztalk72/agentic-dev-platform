# Architecture

## High-Level Layers
1. **Input Layer**: text prompt, structured log parser, video keyframe extractor + VLM summarizer.
2. **Graph Core**: Asset Graph (permanent) + Exploration Graph (per-task, archived on completion). SQLite-backed, event bus notifies on mutation.
3. **Agent Runtime**: Orchestrator + N workers. Each worker is a thin LLM-calling loop with a fixed toolset. Orchestrator is the only component that creates intents.
4. **Tool Layer**: bash/shell, HTTP client, file read/write, VLM frame analysis, report generation.
5. **HITL Gate Layer**: intercepts tagged tool calls (deploy, schema change, payment/auth calls), pauses execution, prompts for approval via CLI, resumes on yes.
6. **Dashboard/CLI Layer**: reads asset graph, prints or serves state.

## Event Loop (single process, asyncio)
```
while True:
    event = await bus.get()          # graph mutation
    if event.type == "GRAPH_MUTATION":
        await orchestrator.wake(event)
        intents = orchestrator.plan() # reads exploration graph + shared todo
        for intent in intents:
            if intent.requires_gate:
                approved = await hitl_gate.ask(intent)
                if not approved: continue
            result = await worker.run(intent)
            await graph.write(result)  # triggers next mutation
```

## Data Model (SQLite)
- `assets(id, type, name, parent_id, dedup_key, payload_json, created_at)`
- `explorations(id, task_id, node_type, content, parent_node_id, edge_type, asset_anchor_id, created_at)`
- `tasks(id, status, goal, created_at, completed_at)`
- `archived_explorations(id, task_id, snapshot_json, archived_at)`
- `audit_log(id, actor, action, detail_json, created_at)`

## VLM Pipeline
1. Receive <=30s clip.
2. Scene-change detection (simple histogram diff threshold).
3. Sample 1 fps, cap 12 keyframes.
4. Send each keyframe + short context prompt to VLM.
5. VLM returns structured summary -> hint nodes in exploration graph.

## Worker Toolsets
- Collector: log parser, VLM client.
- Analyst: graph query, cross-worker trace search.
- PRD: file write, graph query.
- Reviewer: graph query, diff tool.
- Dashboard: graph query, render.

## Extension Points
- Graph store: SQLite -> PostgreSQL via adapter interface.
- LLM provider: env-var configurable.
- HITL gate: CLI prompt -> Slack/web UI later.
