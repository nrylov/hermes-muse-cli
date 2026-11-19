# hermes-muse-cli

[![ci](https://github.com/nrylov/hermes-muse-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/nrylov/hermes-muse-cli/actions/workflows/ci.yml)

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) skill for delegating coding
tasks to Meta's Muse Code CLI (`muse`), with a stdlib helper that runs one headless task,
parses the JSONL event stream, and reports the git diff.

| Skill | What it does | Helper |
|---|---|---|
| [`muse-cli`](skills/muse-cli) | Headless Muse Code sessions, diff review | `muse_run.py` (stdlib) |

## Install

```bash
cp -r skills/muse-cli ~/.hermes/skills/autonomous-ai-agents/
```

## Try it

```bash
python3 -m unittest discover tests -v
python3 scripts/validate_skills.py
```

## Requirements

- `muse` CLI on PATH (tested with 1.4.15), signed in.
- Target directory must be a git repo.

## Safety

The helper runs with `--approval-mode never`, so Muse edits without prompting. Use it only in
an isolated worktree or scratch repo, and review the diff.

MIT licensed.
