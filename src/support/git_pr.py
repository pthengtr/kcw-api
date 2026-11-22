from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        args,
        cwd=str(cwd),
        check=check,
        text=True,
        capture_output=True,
        env=merged,
    )


def repo_root_for(target_source: str) -> Path:
    if target_source == "kcw-api":
        return Path(
            os.getenv("SUPPORT_REPO_KCW_API", "/home/hqadmin/projects/kcw-api")
        )
    if target_source == "kcw-v2":
        return Path(
            os.getenv("SUPPORT_REPO_KCW_V2", "/home/hqadmin/projects/kcw-v2")
        )
    raise ValueError(f"Unknown target_source: {target_source}")


def worktrees_root() -> Path:
    root = Path(
        os.getenv(
            "SUPPORT_WORKTREES_DIR",
            "/home/hqadmin/projects/.support-worktrees",
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def prepare_worktree(ticket_id: str, target_source: str) -> tuple[Path, str]:
    """Fetch main and create a dedicated worktree + branch. Returns (cwd, branch)."""
    main_repo = repo_root_for(target_source)
    short = ticket_id.replace("-", "")[:10]
    branch = f"support/{short}"
    worktree = worktrees_root() / f"{target_source}-{short}"

    if worktree.exists():
        shutil.rmtree(worktree)

    _run(["git", "fetch", "origin", "main"], cwd=main_repo)
    # Drop stale remote branch tip if we re-run the same short id.
    _run(
        ["git", "worktree", "prune"],
        cwd=main_repo,
        check=False,
    )
    _run(
        [
            "git",
            "worktree",
            "add",
            "-B",
            branch,
            str(worktree),
            "origin/main",
        ],
        cwd=main_repo,
    )
    return worktree, branch


def remove_worktree(ticket_id: str, target_source: str) -> None:
    main_repo = repo_root_for(target_source)
    short = ticket_id.replace("-", "")[:10]
    worktree = worktrees_root() / f"{target_source}-{short}"
    if worktree.exists():
        _run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=main_repo,
            check=False,
        )
        if worktree.exists():
            shutil.rmtree(worktree, ignore_errors=True)


def has_changes(cwd: Path) -> bool:
    staged = _run(["git", "status", "--porcelain"], cwd=cwd)
    return bool(staged.stdout.strip())


def commit_all(cwd: Path, message: str) -> None:
    _run(["git", "add", "-A"], cwd=cwd)
    if not has_changes(cwd):
        return
    _run(["git", "commit", "-m", message], cwd=cwd)


def push_and_pr_merge(
    cwd: Path,
    *,
    branch: str,
    title: str,
    body: str,
) -> tuple[str, str | None]:
    """Push branch, create PR, squash-merge. Returns (pr_url, merge_sha)."""
    _run(["git", "push", "-u", "origin", f"HEAD:{branch}", "--force-with-lease"], cwd=cwd)

    create = _run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            title[:200],
            "--body",
            body,
        ],
        cwd=cwd,
        check=False,
    )
    if create.returncode != 0:
        # Maybe PR already exists for this branch.
        view = _run(
            ["gh", "pr", "view", branch, "--json", "url", "--jq", ".url"],
            cwd=cwd,
            check=False,
        )
        if view.returncode != 0 or not view.stdout.strip():
            raise RuntimeError(
                f"gh pr create failed: {create.stderr or create.stdout}"
            )
        pr_url = view.stdout.strip()
    else:
        pr_url = create.stdout.strip().splitlines()[-1].strip()

    merge = _run(
        [
            "gh",
            "pr",
            "merge",
            pr_url,
            "--squash",
            "--delete-branch",
            "--admin",
        ],
        cwd=cwd,
        check=False,
    )
    if merge.returncode != 0:
        # Retry without --admin in case admin flag is unavailable.
        merge = _run(
            [
                "gh",
                "pr",
                "merge",
                pr_url,
                "--squash",
                "--delete-branch",
            ],
            cwd=cwd,
            check=False,
        )
    if merge.returncode != 0:
        raise RuntimeError(f"gh pr merge failed: {merge.stderr or merge.stdout}")

    sha_proc = _run(
        ["gh", "pr", "view", pr_url, "--json", "mergeCommit", "--jq", ".mergeCommit.oid"],
        cwd=cwd,
        check=False,
    )
    merge_sha = sha_proc.stdout.strip() or None
    return pr_url, merge_sha


def run_local_agent(*, cwd: Path, prompt: str, timeout_sec: int = 45 * 60) -> str:
    agent_bin = os.getenv("SUPPORT_AGENT_BIN") or os.getenv("CURSOR_AGENT") or "agent"
    api_key = os.getenv("CURSOR_API_KEY") or ""
    cmd = [
        agent_bin,
        "-p",
        "--force",
        "--output-format",
        "text",
        prompt,
    ]
    env = {}
    if api_key:
        env["CURSOR_API_KEY"] = api_key
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env={**os.environ, **env},
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"agent failed ({proc.returncode}): {(proc.stderr or proc.stdout)[-4000:]}"
        )
    return (proc.stdout or "")[-8000:]
