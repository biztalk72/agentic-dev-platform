# Design

## Design Principles
1. **Lineage first**: every finding must trace back to a fact, which traces to an input (prompt/log/frame).
2. **LLM submits raw info; code computes structure**: dedup keys, hierarchy, edge wiring are deterministic.
3. **Small context windows**: workers receive only the subgraph relevant to their intent, not the whole graph.
4. **Fail loud, recover soft**: a worker error is recorded as a fact (not silently dropped) and the orchestrator may retry or re-route.

## UI / CLI
- MVP is CLI-first. Commands: `run`, `status`, `graph`, `archive`, `approve`.
- Optional Next.js dashboard served at localhost:3000 showing asset graph (force-directed) and exploration timeline.

## VLM Frame Summary Format (JSON)
```json
{
  "scene": "login page",
  "elements": ["email input", "password input", "submit button (disabled)"],
  "anomalies": ["layout shift on mobile width"],
  "confidence": 0.8
}
```

## HITL Gate UX
- CLI prints: `[GATE] Intent: deploy to staging. Approve? [y/N]`
- Timeout (default 10 min) = deny, logged to audit_log.

## Error & Retry Policy
- Worker tool failure: 2 retries with backoff, then record failure fact.
- LLM call failure: 1 retry, then fail the intent; orchestrator decides.

## Cost Controls
- Keyframe cap (12/clip) and 30s clip limit are hard constraints in the extractor.
- Worker context trimmed to relevant subgraph + last 5 findings.
- VLM calls batched per clip, not per frame where possible.
