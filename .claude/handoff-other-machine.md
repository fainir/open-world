# Continuation Prompt - paste into a new Claude Code session on the other computer

Copy everything between the `---` markers into the new session's first message.

---

We're continuing work that was started on my other Mac. Read this whole brief, then act on the outstanding items in order.

## What we already did (don't redo)

I asked Claude to commit + push every change across every git repo on the other machine. We took the "safe" path: real source changes were committed and pushed, but we skipped junk (node_modules, __pycache__, .DS_Store, *.log, *.pid, .claude/worktrees, .claude/handoff.md, .claude/settings.local.json, .mcp.json) and secrets (client_secrets.json, token.pickle).

Pushed clean on the other machine: open-world, personal-website, cloudbot-panel, gatherate, plainer, plainer-code, full-stack-job-interview, phone-agent, video-maker, qa-autopilot. instagram-clone was committed locally (no remote).

## Three items still need attention - these are your job now

1. **proto-multi** (`~/Documents/GitHub/proto-multi`) — `git status` showed the entire `control-plane/` directory as deleted (98 files). I did NOT commit this because it looks unintentional - possibly a move/rename that didn't get staged correctly, or files that should be restored from a sibling worktree. **Investigate before doing anything**: run `git log -- control-plane/` to see history, check if there's a sibling repo or worktree the code moved to, and ask me before committing the delete or running `git restore`.

2. **video-maker** (`~/Documents/GitHub/video-maker`) — `backend/client_secrets.json` and `backend/token.pickle` are sitting in the working tree as untracked files. These are Google API credentials and MUST NOT be committed. Add them to `.gitignore` so they stop appearing as floating untracked files. Also add `backend/automation.log` to `.gitignore`. Commit just the gitignore change.

3. **sumbli-client** (`~/Documents/sumbli-client`) — has a real `package.json` modification but the commit is blocked by a pre-commit hook (`./node_modules/pre-commit/hook` which doesn't exist because node_modules isn't installed). Either `cd ~/Documents/sumbli-client && npm install` then retry the commit, or check whether this repo is still active at all (last commit was 2021).

## Rule and hook to replicate on this machine

On the other Mac I added two pieces of enforcement so I never leave work uncommitted again. Mirror them here:

a) Append this to `~/.claude/rules/code-quality.md` under the `## Git` section:

```
### ALWAYS commit and push (work-loss prevention - non-negotiable)

User has lost files before because work was left uncommitted. Treat any work that isn't pushed to a remote as work that doesn't exist yet.

- After EVERY meaningful change to source files, commit immediately. Do not batch hours of work into one commit at the end.
- After EVERY commit, push to the remote. Local commits are not durable - a disk failure, a wrong `git reset`, or a stray `rm -rf` loses them.
- Before ending a session or marking a task done: run `git status`. If anything is uncommitted or unpushed, commit and push it FIRST.
- If a remote doesn't exist for the repo, tell the user and ask if they want one created (`gh repo create`). Do not silently leave work unpushed.
- Exception: files that legitimately should not be committed (secrets, build artifacts, node_modules, __pycache__, .DS_Store, log/pid files, local-only Claude state). Add these to `.gitignore` instead of leaving them as floating untracked files.
- When in doubt, commit. A messy commit history is recoverable; lost work is not.
```

b) Create `~/.claude/hooks/enforce-git-clean.sh` (chmod +x) - I'll paste the script below - and add it to the `Stop` hooks array in `~/.claude/settings.json` after `enforce-memory.sh`. The hook blocks session-stop when there are modified tracked files or unpushed commits, but doesn't block on untracked files or repos with no remote (it asks me about creating one in that case).

The script lives in the source repo I'm sending you - check `~/Documents/GitHub/open-world/.claude/enforce-git-clean-script.sh` after cloning, or grab it from the previous machine.

## Order of operations

1. Pull this repo (`open-world`) and read `.claude/handoff-other-machine.md` (this file) plus `.claude/enforce-git-clean-script.sh`.
2. Mirror the rule + hook (item a and b above).
3. Investigate proto-multi (item 1).
4. Fix video-maker gitignore (item 2).
5. Decide on sumbli-client (item 3).
6. Then `git status` across all repos and report what's still dirty.

Do NOT just commit-and-push everything blindly on this machine without going through the safe filter. Skip node_modules deletions, __pycache__, .DS_Store, *.log, *.pid, secrets, and `.claude/` session-state files (handoff.md, worktrees/, settings.local.json, tester-progress.log, screenshots).

---
