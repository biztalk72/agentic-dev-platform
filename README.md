# agentic-dev-platform

Multi-agent development platform (MVP) with:

- **Dual-graph core**: permanent Asset Graph + per-task Exploration Graph (archived on completion), inspired by ARTEX's architecture.
- **Multimodal input**: text prompts, structured logs, and <=30s screen videos (1fps keyframes, max 12/clip) analyzed by a VLM into hint nodes.
- **Event-driven closed loop**: orchestrator wakes on graph mutations, dispatches intents to workers, writes results back.
- **Human-in-the-loop gates**: deployment, DB schema changes, and payment/auth calls require CLI approval.
- **Skills system**: drop a `SKILL.md` into `skills/` to teach workers new capabilities without core changes.
- **Claude Code compatible**: prompts and skills are plain markdown; open this repo in Claude Code and ask it to build or extend.

## Quick start (GitHub Codespaces / any machine with Python 3.12+)

```bash
chmod +x build.sh
./build.sh
```

Or manually:

```bash
pip3 install -r requirements.txt
python3 -m src.main --demo
python3 -m http.server 8765 --directory web
```

The demo writes `web/data.json`. Open `http://127.0.0.1:8765/` to read the asset, task, and exploration tables. `web/data.json` is generated and is not committed.

## Docs

- [PRD.md](PRD.md) - product requirements (includes keyframe limits, HITL gate list, archival policy)
- [architecture.md](architecture.md) - layers, event loop, data model, VLM pipeline
- [design.md](design.md) - principles, CLI/UI, error policy, cost controls
- [skills/SKILL.md](skills/SKILL.md) - how to add skills

## License

AGPL-3.0
