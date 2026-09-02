"""Fork upstream sync while a maintained custom branch is checked out."""

import subprocess
from pathlib import Path

from hermes_cli import update_cmd


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _commit(repo: Path, filename: str, content: str, message: str) -> None:
    (repo / filename).write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-qm", message)


def test_sync_updates_fork_main_without_checking_out_custom_branch(tmp_path, capsys):
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    _git(upstream, "config", "user.email", "upstream@example.invalid")
    _git(upstream, "config", "user.name", "Upstream")
    _commit(upstream, "version.txt", "one\n", "upstream one")

    fork_remote = tmp_path / "fork.git"
    _git(tmp_path, "init", "-q", "--bare", str(fork_remote))
    _git(upstream, "remote", "add", "fork", str(fork_remote))
    _git(upstream, "push", "-q", "fork", "main")

    checkout = tmp_path / "checkout"
    _git(tmp_path, "clone", "-q", "-b", "main", str(fork_remote), str(checkout))
    _git(checkout, "config", "user.email", "maintainer@example.invalid")
    _git(checkout, "config", "user.name", "Maintainer")
    _git(checkout, "remote", "add", "upstream", str(upstream))
    _git(checkout, "checkout", "-qb", "local")
    _commit(checkout, "local.txt", "fork patch\n", "fork patch")

    _commit(upstream, "version.txt", "two\n", "upstream two")
    # The fork remote remains at the old tip; only the upstream remote advances.
    # Keep the simulated fork's origin/main at the old tip so the updater must
    # discover upstream/main and advance the local main ref itself.
    _git(checkout, "fetch", "-q", "origin", "main")
    old_main = _git(checkout, "rev-parse", "refs/heads/main").stdout.strip()
    local_tip = _git(checkout, "rev-parse", "HEAD").stdout.strip()

    assert update_cmd._sync_with_upstream_if_needed(["git"], checkout) is True

    assert _git(checkout, "branch", "--show-current").stdout.strip() == "local"
    assert _git(checkout, "rev-parse", "refs/heads/main").stdout.strip() != old_main
    assert _git(checkout, "rev-parse", "refs/remotes/origin/main").stdout.strip() == _git(
        checkout, "rev-parse", "refs/heads/main"
    ).stdout.strip()
    assert _git(checkout, "rev-parse", "HEAD").stdout.strip() == local_tip
    assert (checkout / "local.txt").read_text(encoding="utf-8") == "fork patch\n"
    assert (checkout / "version.txt").read_text(encoding="utf-8") == "one\n"
    assert "Syncing fork" in capsys.readouterr().out
