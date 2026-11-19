---
name: muse-cli
description: Delegate coding tasks to Meta's Muse Code CLI, headless.
version: 0.1.0
author: Nikolai Rylov (nrylov), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [coding-agent, muse, meta, headless, code-edit]
    related_skills: [coding-agents, grok-cli]
---

# Muse Code CLI

Run `muse` (Muse Code 1.4.15, Meta's terminal coding agent) as a delegated coding
agent. Use it when the user asks for Muse or "the meta CLI" by name, or for a
bounded edit that a second agent should make in an isolated repo.

## When to Use

- User names Muse / Muse Code / "meta CLI".
- A bounded change with clear acceptance criteria.

Do not use for vague exploration. Hermes reviews every diff before accepting it.

## Prerequisites

- `muse --version` works (tested: `1.4.15`). Binary at `~/.local/bin/muse`.
- Signed in with `muse login` (or a provider key via `muse auth`). Check with `muse usage`.
- Target directory is a git repo root. Muse's trust gating needs the workspace trusted to load project skills and MCP servers; a headless run does not need that for plain edits.

## Headless one-shot (preferred)

```
terminal(command="python3 skills/muse-cli/scripts/muse_run.py /tmp/task.txt --cwd /path/to/repo --max-steps 10")
```

Write the prompt to a file with `write_file` first. The helper returns `ok`,
`terminal`, `text`, `calls`, `failed_calls`, `models`, `diff_stat` and `untracked`.

Or call Muse directly:

```
muse exec --json --prompt-file task.txt --approval-mode never --max-model-steps 10
```

`--json` emits JSONL events. The final answer is in the `run.terminal.completed`
event (`payload.terminal` and `payload.text`). Token usage is in `run.usage`.

## Approval modes (verified)

| Mode | Result |
|---|---|
| `never` | Edits applied, no prompts. Use this for headless work in a scratch or worktree repo. |
| `on-request` (default) | Prompts for approval. A headless run cannot answer, so it is not suitable for automation. |
| `untrusted` | Most restrictive. Not tested. |

`--approval-mode auto` is not valid. Use `never` for headless work, and review the diff afterwards.

## Verification (always)

1. `git diff --stat` in the repo; only the intended files changed.
2. Run the project's tests yourself. Do not trust Muse's claim that tests pass.
3. Read the diff before committing or merging.

## Pitfalls

- `muse exec` can exit 0 on a non-completed terminal state. Check `terminal == "completed"`; the helper does.
- The workspace is untrusted by default, so project skills and `.mcp.json` servers are not loaded. Pass `--trust-workspace` only for repos you trust.
- `--yolo` disables approval and the sandbox. Avoid it.
- `muse usage` may report no data for a new subscription window; this is not an error.
- The helper defaults to `--approval-mode never`, which lets Muse edit without asking. Only run it in an isolated worktree or scratch repo.
