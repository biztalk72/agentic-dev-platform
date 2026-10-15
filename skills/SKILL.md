# Skills: How to Extend This Platform

A skill is a named, versioned instruction pack that teaches a worker a specialized capability without changing core code.

## Skill File Format
`skills/<skill_name>/SKILL.md` with YAML frontmatter:
```yaml
---
name: security-review
version: 1.0.0
worker: analyst
tools: [graph_query, bash, http]
---
```
Body: step-by-step instructions, example inputs/outputs, and red lines (things the skill must never do).

## Bundled Skills (MVP)
1. **prd-drafting**: PRD Worker reads requirements + findings, writes `output/PRD.md`, records path as a fact.
2. **lineage-check**: Reviewer verifies every finding has a prove-chain to an input node; flags orphans.
3. **hitl-gate-check**: pre-flight scan that flags any intent touching deploy/schema/payment/auth.
4. **archive-policy**: on task completion, snapshots exploration graph to `archived_explorations`, prunes hot store.

## Creating a New Skill
1. Create `skills/<name>/SKILL.md`.
2. Register in `skills/registry.yaml`.
3. Restart or hot-reload; orchestrator picks it up on next wake.
4. No core code changes required.

## Red Lines (all skills)
- Never execute code against production.
- Never bypass HITL gates.
- Never delete asset graph nodes (archive only).
