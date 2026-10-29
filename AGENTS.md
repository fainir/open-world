# OpenWorld - agent notes

Production work follows the ship and production-ready skills in ~/.agents/skills/ (shared by Codex and
Claude Code). READINESS.md is the definition of done; PRODUCT.md is the spec; GOAL.md is the goal sentence.

- Run / test / deploy: see PRODUCT.md "Stack and hosting".
- Owner-only items: one exact action at a time (owner-actions skill). Third-party reviews are waiting rows.
- Evidence under qa/. Commit and push after each verified flow. Only commit files you changed.

## Working here
- Use qa/local.py with an explicit minimal environment for offline QA; app/run.py loads local .env. The --lightweight-game fixture proves functional account/editor UI only and must never be used as a game or performance pass. (2026-10-29)
- Account restore requires current surviving deleted-accounts.json evidence. Source recovery.py stays stdlib-only because the existing independent mirror copies it outside the app package; update that existing runtime helper with the coordinator rollout, retaining key/config/CLI. (2026-10-29)
- Public base games load directly in their existing opaque iframe response; private versions retain bearer-authenticated fetch/srcdoc and a revision guard so delayed HTML cannot repaint after logout. Verify actual Start/gameplay separately from functional fixtures. (2026-10-29)
