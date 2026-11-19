#!/usr/bin/env python3
"""Run one headless Muse Code task and print a compact JSON summary.

Stdlib only; written for Python 3.9+. Wraps `muse exec --json --prompt-file ...`
and parses the JSONL event stream: the final text and terminal state come from
run.terminal.completed, token usage from run.usage, and the git diff from the repo.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

APPROVAL_MODES = ["untrusted", "on-request", "never"]


def build_command(prompt_file, approval_mode, max_steps, model=None):
    cmd = ["muse", "exec", "--json", "--prompt-file", prompt_file,
           "--approval-mode", approval_mode]
    if max_steps:
        cmd += ["--max-model-steps", str(max_steps)]
    if model:
        cmd += ["--model", model]
    return cmd


def parse_events(jsonl_text):
    """Return (session_id, terminal_record_payload, usage_payload) from Muse's JSONL stream."""
    session_id, terminal, usage = None, None, None
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)  # raises ValueError on malformed output
        if session_id is None and rec.get("stream", {}).get("kind") == "session":
            session_id = rec["stream"].get("id")
        ptype = rec.get("payload_type")
        if ptype == "run.terminal.completed":
            terminal = rec.get("payload", {})
        elif ptype == "run.usage":
            usage = rec.get("payload", {})
    return session_id, terminal, usage


def summarize(jsonl_text):
    session_id, terminal, usage = parse_events(jsonl_text)
    if terminal is None:
        raise ValueError("no run.terminal.completed event in output")
    models = (usage or {}).get("models", [])
    return {
        "session_id": session_id,
        "terminal": terminal.get("terminal"),
        "text": terminal.get("text", ""),
        "reason": terminal.get("reason"),
        "calls": (usage or {}).get("calls"),
        "failed_calls": (usage or {}).get("failed_calls"),
        "models": models,
    }


def git_diff_stat(cwd):
    try:
        out = subprocess.run(["git", "-C", cwd, "diff", "--stat"], capture_output=True,
                             text=True, timeout=30)
        untracked = subprocess.run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"],
                                   capture_output=True, text=True, timeout=30)
        return {"diff_stat": out.stdout.strip(),
                "untracked": [l for l in untracked.stdout.splitlines() if l]}
    except (OSError, subprocess.SubprocessError):
        return {"diff_stat": None, "untracked": []}


def run(prompt_file, cwd, approval_mode="never", max_steps=10, timeout=600, model=None):
    if not shutil.which("muse"):
        return {"ok": False, "error": "muse binary not found on PATH"}
    if not os.path.isdir(os.path.join(cwd, ".git")):
        return {"ok": False, "error": "cwd is not a git repo root: %s" % cwd}
    cmd = build_command(prompt_file, approval_mode, max_steps, model)
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timed out after %ss" % timeout}
    result = {"ok": False, "exit_code": proc.returncode,
              "stderr_tail": proc.stderr.strip().splitlines()[-3:]}
    try:
        result.update(summarize(proc.stdout))
        # Only a completed run counts as success; the process can exit 0 on other terminal states.
        result["ok"] = proc.returncode == 0 and result.get("terminal") == "completed"
    except ValueError as exc:
        result["error"] = "could not parse muse JSON output: %s" % exc
        result["raw_tail"] = proc.stdout[-500:]
    result.update(git_diff_stat(cwd))
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("prompt_file", help="file containing the task prompt")
    p.add_argument("--cwd", required=True, help="git repo root to work in")
    p.add_argument("--approval-mode", default="never", choices=APPROVAL_MODES)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--model")
    args = p.parse_args(argv)
    result = run(os.path.abspath(args.prompt_file), os.path.abspath(args.cwd),
                 args.approval_mode, args.max_steps, args.timeout, args.model)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
