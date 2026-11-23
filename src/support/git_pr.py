from __future__ import annotations

import os
import re
import signal
import shutil
import subprocess
import threading
import time
from pathlib import Path


def base_branch() -> str:
    """Both kcw-api and kcw-v2 use `master` (not `main`)."""
    return (os.getenv("SUPPORT_BASE_BRANCH") or "master").strip() or "master"


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
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=True,
        env=merged,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"Command {args!r} failed ({proc.returncode})"
            + (f": {detail}" if detail else "")
        )
    return proc


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
    """Fetch base branch and create a dedicated worktree. Returns (cwd, branch)."""
    main_repo = repo_root_for(target_source)
    base = base_branch()
    short = ticket_id.replace("-", "")[:10]
    branch = f"support/{short}"
    worktree = worktrees_root() / f"{target_source}-{short}"

    if worktree.exists():
        shutil.rmtree(worktree)

    _run(["git", "fetch", "origin", base], cwd=main_repo)
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
            f"origin/{base}",
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


def _pr_state(cwd: Path, pr_url: str) -> tuple[str | None, str | None]:
    """Return (state, merge_sha) for a PR URL."""
    view = _run(
        [
            "gh",
            "pr",
            "view",
            pr_url,
            "--json",
            "state,mergeCommit",
            "--jq",
            "[.state, (.mergeCommit.oid // \"\")] | @tsv",
        ],
        cwd=cwd,
        check=False,
    )
    if view.returncode != 0 or not view.stdout.strip():
        return None, None
    parts = view.stdout.strip().split("\t")
    state = parts[0] if parts else None
    sha = parts[1] if len(parts) > 1 and parts[1] else None
    return state, sha


def _merge_output_means_already_merged(text: str) -> bool:
    low = (text or "").lower()
    return "already merged" in low or "pull request is not mergeable: closed" in low


def push_and_pr_merge(
    cwd: Path,
    *,
    branch: str,
    title: str,
    body: str,
) -> tuple[str, str | None]:
    """Push branch, create PR, squash-merge. Returns (pr_url, merge_sha).

    Do not pass ``--delete-branch`` to ``gh pr merge`` from a support worktree:
    after merge, gh tries to check out the base branch locally, which fails when
    ``master`` is already checked out in the primary clone.
    """
    _run(["git", "push", "-u", "origin", f"HEAD:{branch}", "--force-with-lease"], cwd=cwd)

    create = _run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch(),
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
        # Maybe PR already exists for this branch (or agent already opened one).
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

    state, merge_sha = _pr_state(cwd, pr_url)
    if state == "MERGED":
        # Agent may have already merged; treat as success.
        _run(["git", "push", "origin", "--delete", branch], cwd=cwd, check=False)
        return pr_url, merge_sha

    merge = _run(
        [
            "gh",
            "pr",
            "merge",
            pr_url,
            "--squash",
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
            ],
            cwd=cwd,
            check=False,
        )

    out = (merge.stderr or merge.stdout or "").strip()
    state, merge_sha = _pr_state(cwd, pr_url)
    if merge.returncode != 0 and state != "MERGED" and not _merge_output_means_already_merged(out):
        raise RuntimeError(f"gh pr merge failed: {out}")

    if state != "MERGED":
        # Race: merge reported already-merged; re-check once.
        state, merge_sha = _pr_state(cwd, pr_url)
    if state != "MERGED":
        raise RuntimeError(f"gh pr merge failed: {out or 'PR not merged'}")

    # Remote-only cleanup; never ask gh to switch this worktree onto master.
    _run(["git", "push", "origin", "--delete", branch], cwd=cwd, check=False)
    return pr_url, merge_sha


def data_query_cwd() -> Path:
    """Working directory for answer-only data_query tickets (no git worktree)."""
    raw = (
        os.getenv("SUPPORT_DATA_QUERY_CWD")
        or "/home/hqadmin/projects/kcw-analytic"
    ).strip()
    path = Path(raw)
    if not path.is_dir():
        raise RuntimeError(f"SUPPORT_DATA_QUERY_CWD is not a directory: {path}")
    return path


# Broad home / FUSE scans hang on rclone mounts under ~/mnt. Kill early.
_BROAD_FIND_RE = re.compile(
    r"(?:^|\s)(?:find|fd|fdfind)\s+(?:-[^\s]+\s+)*"
    r"(?:/home/hqadmin(?:/mnt)?(?:\s|$)|/\s|/home(?:\s|$))",
)
_MNT_SCAN_RE = re.compile(r"/home/hqadmin/mnt(?:/|\s|$)")


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()


def _read_stat_start_ticks(pid: int) -> int | None:
    try:
        # /proc/<pid>/stat field 22 is starttime (clock ticks after boot).
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        return int(fields[21])
    except (OSError, IndexError, ValueError):
        return None


def _process_age_sec(pid: int, *, ticks_per_sec: float, boot_time: float) -> float:
    start = _read_stat_start_ticks(pid)
    if start is None:
        return 0.0
    return max(0.0, time.time() - (boot_time + start / ticks_per_sec))


def _boot_time_sec() -> float:
    try:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except OSError:
        pass
    return time.time()


def _iter_descendant_pids(root_pid: int) -> set[int]:
    """Best-effort walk of /proc for children of root_pid (incl. root)."""
    children: dict[int, list[int]] = {}
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            try:
                status = (entry / "status").read_text()
            except OSError:
                continue
            ppid = None
            for line in status.splitlines():
                if line.startswith("PPid:"):
                    ppid = int(line.split()[1])
                    break
            if ppid is None:
                continue
            children.setdefault(ppid, []).append(pid)
    except OSError:
        return {root_pid}

    found = {root_pid}
    stack = [root_pid]
    while stack:
        cur = stack.pop()
        for child in children.get(cur, []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def _is_dangerous_scan(cmdline: str, *, worktree: Path) -> bool:
    """True for home-wide / mount-wide filesystem crawls that wedge on FUSE."""
    if not cmdline:
        return False
    wt = str(worktree)
    # Explicit worktree-scoped find is OK.
    if wt in cmdline and not _MNT_SCAN_RE.search(cmdline):
        return False
    if _BROAD_FIND_RE.search(cmdline):
        return True
    if _MNT_SCAN_RE.search(cmdline) and re.search(
        r"(?:^|\s)(?:find|fd|fdfind|rg|grep|locate)\s", cmdline
    ):
        return True
    return False


def _kill_process_group(pid: int, *, sig: int = signal.SIGKILL) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def _watch_and_reap_dangerous_scans(
    root_pid: int,
    *,
    worktree: Path,
    stop: threading.Event,
    grace_sec: float,
) -> list[str]:
    """Kill descendant scans that crawl $HOME or ~/mnt (rclone FUSE hang risk)."""
    killed: list[str] = []
    ticks = float(os.sysconf("SC_CLK_TCK"))
    boot = _boot_time_sec()
    while not stop.wait(2.0):
        for pid in _iter_descendant_pids(root_pid):
            if pid == root_pid:
                continue
            cmd = _read_cmdline(pid)
            if not _is_dangerous_scan(cmd, worktree=worktree):
                continue
            age = _process_age_sec(pid, ticks_per_sec=ticks, boot_time=boot)
            if age < grace_sec:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(f"pid={pid} age={age:.0f}s cmd={cmd[:240]}")
                print(
                    f"[support] killed dangerous scan: pid={pid} "
                    f"age={age:.0f}s cmd={cmd[:200]}"
                )
            except OSError:
                pass
    return killed


def run_local_agent(
    *,
    cwd: Path,
    prompt: str,
    timeout_sec: int | None = None,
    sandbox: bool = True,
) -> str:
    """Run Cursor CLI agent in ``cwd``.

    Hardening vs FUSE hangs under ``~/mnt``:
    - optional ``--sandbox enabled`` (code tickets) to keep tools in-workspace
    - own process group so timeouts can SIGKILL the whole tree
    - watchdog kills home-wide / mount-wide ``find`` scans quickly
    """
    agent_bin = os.getenv("SUPPORT_AGENT_BIN") or os.getenv("CURSOR_AGENT") or "agent"
    api_key = os.getenv("CURSOR_API_KEY") or ""
    if timeout_sec is None:
        timeout_sec = int(os.getenv("SUPPORT_AGENT_TIMEOUT_SEC", str(45 * 60)))
    grace_sec = float(os.getenv("SUPPORT_SCAN_KILL_GRACE_SEC", "12"))
    sandbox_env = (os.getenv("SUPPORT_AGENT_SANDBOX") or "").strip().lower()
    if sandbox_env in ("0", "false", "off", "disabled"):
        sandbox = False
    elif sandbox_env in ("1", "true", "on", "enabled"):
        sandbox = True

    cmd = [
        agent_bin,
        "-p",
        "--force",
        "--trust",
        "--workspace",
        str(cwd),
        "--output-format",
        "text",
    ]
    if sandbox:
        cmd.extend(["--sandbox", "enabled"])
    cmd.append(prompt)

    env = {**os.environ}
    if api_key:
        env["CURSOR_API_KEY"] = api_key

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    assert proc.pid is not None

    stop = threading.Event()
    killed_scans: list[str] = []

    def _watch() -> None:
        killed_scans.extend(
            _watch_and_reap_dangerous_scans(
                proc.pid,
                worktree=cwd.resolve(),
                stop=stop,
                grace_sec=grace_sec,
            )
        )

    watcher = threading.Thread(target=_watch, name="support-scan-watch", daemon=True)
    watcher.start()

    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc.pid)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            _kill_process_group(proc.pid)
            stdout, stderr = proc.communicate()
        raise RuntimeError(
            f"agent timed out after {timeout_sec}s: "
            f"{(stderr or stdout or '')[-4000:]}"
        ) from None
    finally:
        stop.set()
        watcher.join(timeout=5)
        if proc.poll() is None:
            _kill_process_group(proc.pid)

    if proc.returncode != 0:
        detail = (stderr or stdout or "")[-4000:]
        if killed_scans:
            detail = (
                f"{detail}\n[support] also killed dangerous scans: "
                + "; ".join(killed_scans[-5:])
            )
        raise RuntimeError(f"agent failed ({proc.returncode}): {detail}")
    return (stdout or "")[-8000:]
