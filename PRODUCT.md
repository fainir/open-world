# OpenWorld

One line: OpenWorld helps creators describe changes to a browser game, preview private versions and share a chosen game without exposing editor credentials or private chat.

## Who and core job

A creator brings an Anthropic key, edits the existing 3D game in a chat, checks each result and keeps earlier versions. Signed-in users save versions across visits; guests retain a private capability on their device. No app subscription or payment is collected.

## Flows

- Start the existing game and use its controls; a loading/provider error must not discard prior versions.
- Sign up/sign in/out with email or username; errors remain useful and credentials never enter a game document.
- Submit a bounded game change with an explicit key; show one new reversible version only after a complete valid response.
- Reload or select previous private versions; another account or anonymous caller cannot read them.
- Explicitly share/publish/suggest one version; public playback exposes the intended game and description, not chat/history.
- Browse/star public games; empty/error/retry states remain usable.
- Export the caller's profile, chats and games; close that account with clear confirmation and failure recovery.
- Contact the operator and read an accurate privacy policy; contacts are separate from unverified signup emails.

## Non-goals

New gameplay, new model/provider choices, new analytics, paid launches, marketing, account-email verification/recovery service, or a new recovery service. Existing real provider/gameplay/recovery acceptance is retained.

## Success metric

Every engineering row in READINESS has valid real-surface evidence and zero open buildable defects.

## Stack and hosting

FastAPI/Python, SQLAlchemy/SQLite, static vanilla JS studio, Three.js game in an opaque iframe. Existing Railway service and persistent DATA_DIR/VERSIONS_DIR; https://open-world.gg.
Run: `app/venv/bin/python app/run.py` with private local paths and synthetic JWT secret. Tests: `app/venv/bin/python -m unittest discover -s tests -v`. Production deploy/rollback: existing service only, documented in OPERATIONS.md; coordinator handles it.

## Data model

| Entity | User data |
|---|---|
| User | Email, username, password hash, role, auth revision |
| ChatSession/ChatMessage | Owner or guest proof, prompts and assistant messages |
| GameVersion | Owner/session, description, generated HTML file, explicit public/share state |
| Star | Account and public game reference |
| ContactMessage | Separately submitted name/email/message; not linked to an account |

No provider key belongs in server records, exports or logs. The existing studio keeps device credentials outside the opaque game. Server recovery retains seven rotating snapshots and the existing independent encrypted mirror; privacy must state the limits of deleting active records.

## Decisions

- 2026-10-29 - Preserve accepted gameplay, model, sandbox and recovery. Scope new work to missing user-visible data/UX/release controls.
- 2026-10-29 - Export excludes credential hashes and includes owned generated game files. Account closure requires current password plus typed DELETE and must preserve other users.

## Open questions

None required for offline implementation. Provider/account configuration is unchanged.
