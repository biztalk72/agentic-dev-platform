# PRD: Agentic Development Platform (MVP)

## 1. Overview
Multi-agent development platform inspired by ARTEX's dual-graph autonomous penetration architecture, adapted for software development workflows. Agents collaborate via shared state graphs with event-driven closed loops, VLM-based visual input analysis, and human-in-the-loop gates for irreversible actions.

## 2. Goals
- Automate the dev loop: gather requirements -> analyze -> design -> implement -> review -> dashboard.
- Preserve full decision lineage (which intent produced which finding, backed by which evidence).
- Accept multimodal customer input: text prompts, structured logs, and short screen-capture videos.
- Keep irreversible operations behind human approval.

## 3. Input Layer (three branches)
1. **Text prompt / PRD**: customer's natural-language requirements.
2. **Structured logs**: timestamped events with event type, parsed into fact nodes.
3. **Screen-capture video**: max 30-second clips. Keyframe extraction: 1 frame per second, capped at 12 keyframes per clip. Scene-change detection first; only representative frames sent to VLM. VLM summarizes each frame into hint nodes (button states, layout breaks, interaction flows).

## 4. Dual-Graph Core
### 4.1 Asset Graph (global, permanent)
Nodes: component, module, API, data model, dependency. Hierarchy auto-computed by program (domain -> subdomain -> service -> endpoint). Agents submit raw info only; dedup keys computed in code, never by the LLM.

### 4.2 Exploration Graph (per-task, archival)
Nodes: goal, intent, fact, finding, hint. Edges: spawns, derived_from, yields, proves. Anchors link exploration nodes to asset nodes. Completed task exploration graphs move to archive storage; only the asset graph is retained permanently.

## 5. Agent Roles
- **Orchestrator (Planner)**: sole intent generator. Reads exploration graph state, dispatches intents in dependency order, maintains a shared cross-round todo list.
- **Collector Worker**: ingests logs and VLM frame summaries into fact/hint nodes.
- **Analyst Worker**: cross-references facts, produces findings, can search other workers' execution traces.
- **PRD Worker**: reads requirements, drafts/updates PRD, records drafts as facts.
- **Reviewer Worker**: re-reads PRD against findings, emits feedback as new intents back to the orchestrator.
- **Dashboard Worker**: renders project state from the asset graph.

## 6. Event-Driven Closed Loop
Graph mutation -> wake orchestrator -> dispatch intent -> worker executes with real tools -> write results back -> mutation triggers next round, until goal is proved (prove_goal).

## 7. Human-in-the-Loop Gates (approval required)
- Deployment to any environment.
- Database schema changes.
- External payment or authentication-related API calls.
All other operations run automatically. Gates are configurable per project.

## 8. Tech Stack (MVP)
- Backend: Python 3.12, asyncio, standard library only (FastAPI is a future candidate for the API layer).
- Graph store: SQLite (swappable to PostgreSQL).
- LLM: pluggable provider (Anthropic Claude primary for Claude Code compatibility).
- VLM: same provider, frame-summary endpoint.
- Frontend: simple Next.js dashboard (optional for MVP; CLI-first).
- Target runtime: runs on GitHub Codespaces / GitHub Actions without local setup.

## 9. Non-Goals (MVP)
- No multi-tenancy, no auth system, no production hardening.
- No real deployment targets; HITL gates are simulated with CLI prompts.

## 10. Success Criteria
- One end-to-end run: prompt + sample log + 30s sample video -> PRD draft + review cycle + dashboard snapshot, with full lineage visible.
- All HITL gates trigger correctly.
- Archive policy moves completed exploration graphs out of the hot store.
